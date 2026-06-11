"""Provider-health circuit breaker with half-open synthetic probes."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from praetor.auth.principal import InsufficientRoleError, Principal
from praetor.config.health_emit import (
    enqueue_health_alerts_in_transaction,
    new_health_alert_batch_id,
)
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.org_config_sections import ProviderHealthCircuitBreakerPolicy
from praetor.judgment.provider import (
    PROVIDER_HEALTH_CANARY_PAYLOAD,
    JudgmentProvider,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderRefusalError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from praetor.policy.circuit_breaker import BreakerTripResult
from praetor.policy.state import BreakerDomain, init_policy_state_schema
from praetor.state.sqlite_guard import (
    forbid_during_critical_transaction,
    require_critical_transaction,
)

PROVIDER_HEALTH_BREAKER_ALERT_CODE = "provider_health_breaker_open"

_BREAKER_TRIPPING_ERRORS: tuple[type[ProviderError], ...] = (
    ProviderTimeoutError,
    ProviderRefusalError,
    ProviderMalformedResponseError,
    ProviderUnavailableError,
)

_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS provider_health_metrics (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    probe_calls_this_minute INTEGER NOT NULL DEFAULT 0,
    probe_minute_started_at TEXT NOT NULL,
    probe_success_total INTEGER NOT NULL DEFAULT 0,
    probe_failure_total INTEGER NOT NULL DEFAULT 0,
    production_failure_total INTEGER NOT NULL DEFAULT 0,
    production_success_total INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO provider_health_metrics (
    id, probe_minute_started_at
) VALUES (1, '1970-01-01T00:00:00+00:00');
"""


@dataclass(frozen=True)
class ProviderHealthMetrics:
    probe_success_total: int
    probe_failure_total: int
    production_failure_total: int
    production_success_total: int


@dataclass(frozen=True)
class ProviderProbeExecutionResult:
    executed: bool
    probe_success: bool | None = None
    rate_limited: bool = False
    breaker_closed: bool = False


@dataclass(frozen=True)
class _ProviderHealthRow:
    is_open: bool
    half_open: bool
    failure_count: int
    success_count: int
    window_started_at: datetime
    opened_at: datetime | None


def provider_failure_trips_breaker(error: ProviderError) -> bool:
    """Return whether a typed provider failure counts toward breaker tripping."""
    return isinstance(error, _BREAKER_TRIPPING_ERRORS)


@dataclass(frozen=True)
class _ProbeMinuteWindow:
    count: int
    minute_started: datetime


def init_provider_health_breaker_schema(conn: sqlite3.Connection) -> None:
    """Ensure provider-health breaker columns and probe metrics exist."""
    forbid_during_critical_transaction(
        conn, operation="init_provider_health_breaker_schema"
    )
    init_policy_state_schema(conn)
    columns = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(circuit_breaker_state)")
    }
    if "half_open" not in columns:
        conn.execute(
            """
            ALTER TABLE circuit_breaker_state
            ADD COLUMN half_open INTEGER NOT NULL DEFAULT 0
            """
        )
    if "opened_at" not in columns:
        conn.execute(
            """
            ALTER TABLE circuit_breaker_state
            ADD COLUMN opened_at TEXT
            """
        )
    conn.executescript(_METRICS_DDL)


def is_provider_health_breaker_blocking(conn: sqlite3.Connection) -> bool:
    """Return whether production alerts must escalate for provider-health."""
    init_provider_health_breaker_schema(conn)
    row = _fetch_provider_health_row(conn)
    return row.is_open


def is_provider_health_half_open(conn: sqlite3.Connection) -> bool:
    init_provider_health_breaker_schema(conn)
    row = _fetch_provider_health_row(conn)
    return row.is_open and row.half_open


def read_provider_health_metrics(conn: sqlite3.Connection) -> ProviderHealthMetrics:
    init_provider_health_breaker_schema(conn)
    row = conn.execute(
        """
        SELECT probe_success_total,
               probe_failure_total,
               production_failure_total,
               production_success_total
        FROM provider_health_metrics
        WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return ProviderHealthMetrics(0, 0, 0, 0)
    return ProviderHealthMetrics(
        probe_success_total=int(row[0]),
        probe_failure_total=int(row[1]),
        production_failure_total=int(row[2]),
        production_success_total=int(row[3]),
    )


def record_provider_production_failure_in_transaction(
    conn: sqlite3.Connection,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime | None = None,
) -> BreakerTripResult:
    """Record a production provider failure; trip breaker at threshold."""
    require_critical_transaction(conn)
    moment = now or datetime.now(UTC)
    row = _fetch_provider_health_row(conn)
    if row.is_open:
        _increment_production_metric(conn, production_failure=True)
        return BreakerTripResult(newly_opened=False)

    failure_count, success_count, window_started_at = _advance_failure_window(
        row, policy, moment
    )
    failure_count += 1
    success_count = 0
    half_open = False
    opened_at: datetime | None = None
    is_open = False
    newly_opened = False
    batch_id: str | None = None
    emitted: list[str] = []

    if failure_count >= policy.failure_threshold:
        newly_opened = True
        is_open = True
        opened_at = moment
        batch_id = new_health_alert_batch_id()
        alert = SystemHealthAlert(
            alert_code=PROVIDER_HEALTH_BREAKER_ALERT_CODE,
            emitted_at=moment,
        )
        emitted = enqueue_health_alerts_in_transaction(
            conn, [alert], batch_id=batch_id
        )

    _persist_provider_health_row(
        conn,
        is_open=is_open,
        half_open=half_open,
        failure_count=failure_count,
        success_count=success_count,
        window_started_at=window_started_at,
        opened_at=opened_at,
    )
    _increment_production_metric(conn, production_failure=True)

    return BreakerTripResult(
        newly_opened=newly_opened,
        health_alert_batch_id=batch_id,
        emitted_alert_ids=tuple(emitted),
    )


def record_provider_production_success_in_transaction(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> None:
    """Record a successful production provider call (metrics only while closed)."""
    require_critical_transaction(conn)
    row = _fetch_provider_health_row(conn)
    if row.is_open:
        return
    _increment_production_metric(conn, production_failure=False)


def trigger_half_open_probes_by_soc_lead(
    conn: sqlite3.Connection,
    *,
    principal: Principal,
    now: datetime | None = None,
) -> bool:
    """SOC-lead action to enter half-open probe mode when breaker is open."""
    require_critical_transaction(conn)
    if principal.role != "soc_lead":
        raise InsufficientRoleError(
            required_role="soc_lead",
            actual_role=principal.role,
        )
    moment = now or datetime.now(UTC)
    return _enter_half_open(conn, moment=moment)


def maybe_enter_half_open_from_timer(
    conn: sqlite3.Connection,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime | None = None,
) -> bool:
    """Enter half-open when the breaker has been open for ``window_seconds``."""
    require_critical_transaction(conn)
    row = _fetch_provider_health_row(conn)
    if not row.is_open or row.half_open or row.opened_at is None:
        return False
    moment = now or datetime.now(UTC)
    elapsed = (moment - row.opened_at).total_seconds()
    if elapsed < float(policy.window_seconds):
        return False
    return _enter_half_open(conn, moment=moment)


def execute_provider_health_probe(
    conn: sqlite3.Connection,
    provider: JudgmentProvider,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime | None = None,
) -> ProviderProbeExecutionResult:
    """Run a rate-limited synthetic probe while half-open."""
    require_critical_transaction(conn)
    moment = now or datetime.now(UTC)
    row = _fetch_provider_health_row(conn)
    if not row.is_open or not row.half_open:
        return ProviderProbeExecutionResult(executed=False)

    if _probe_rate_limit_exceeded(conn, policy=policy, now=moment):
        return ProviderProbeExecutionResult(executed=False, rate_limited=True)

    probe_result = provider.probe(PROVIDER_HEALTH_CANARY_PAYLOAD)
    _record_probe_call(conn, now=moment)
    if probe_result.success:
        return _record_probe_success(conn, policy=policy, now=moment)
    return _record_probe_failure(conn, now=moment)


def _fetch_provider_health_row(conn: sqlite3.Connection) -> _ProviderHealthRow:
    row = conn.execute(
        """
        SELECT is_open,
               COALESCE(half_open, 0),
               failure_count,
               success_count,
               window_started_at,
               opened_at
        FROM circuit_breaker_state
        WHERE domain = ?
        """,
        (BreakerDomain.PROVIDER_HEALTH.value,),
    ).fetchone()
    if row is None:
        msg = "missing circuit_breaker_state row for provider_health"
        raise RuntimeError(msg)
    opened_raw = row[5]
    return _ProviderHealthRow(
        is_open=bool(int(row[0])),
        half_open=bool(int(row[1])),
        failure_count=int(row[2]),
        success_count=int(row[3]),
        window_started_at=datetime.fromisoformat(str(row[4])),
        opened_at=(
            datetime.fromisoformat(str(opened_raw)) if opened_raw is not None else None
        ),
    )


def _advance_failure_window(
    row: _ProviderHealthRow,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime,
) -> tuple[int, int, datetime]:
    elapsed = (now - row.window_started_at).total_seconds()
    if elapsed >= float(policy.window_seconds):
        return 0, 0, now
    return row.failure_count, row.success_count, row.window_started_at


def _persist_provider_health_row(
    conn: sqlite3.Connection,
    *,
    is_open: bool,
    half_open: bool,
    failure_count: int,
    success_count: int,
    window_started_at: datetime,
    opened_at: datetime | None,
) -> None:
    conn.execute(
        """
        UPDATE circuit_breaker_state
        SET is_open = ?,
            half_open = ?,
            failure_count = ?,
            success_count = ?,
            window_started_at = ?,
            opened_at = ?
        WHERE domain = ?
        """,
        (
            1 if is_open else 0,
            1 if half_open else 0,
            failure_count,
            success_count,
            window_started_at.isoformat(),
            opened_at.isoformat() if opened_at is not None else None,
            BreakerDomain.PROVIDER_HEALTH.value,
        ),
    )


def _enter_half_open(conn: sqlite3.Connection, *, moment: datetime) -> bool:
    row = _fetch_provider_health_row(conn)
    if not row.is_open or row.half_open:
        return False
    _persist_provider_health_row(
        conn,
        is_open=True,
        half_open=True,
        failure_count=row.failure_count,
        success_count=0,
        window_started_at=row.window_started_at,
        opened_at=row.opened_at,
    )
    return True


def _probe_rate_limit_exceeded(
    conn: sqlite3.Connection,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime,
) -> bool:
    window = _current_probe_minute_window(conn, now=now)
    return window.count >= policy.probe_rate_limit_per_minute


def _record_probe_call(conn: sqlite3.Connection, *, now: datetime) -> None:
    window = _current_probe_minute_window(conn, now=now)
    _persist_probe_minute_window(
        conn,
        _ProbeMinuteWindow(
            count=window.count + 1,
            minute_started=window.minute_started,
        ),
    )


def _current_probe_minute_window(
    conn: sqlite3.Connection, *, now: datetime
) -> _ProbeMinuteWindow:
    row = conn.execute(
        """
        SELECT probe_calls_this_minute, probe_minute_started_at
        FROM provider_health_metrics
        WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return _ProbeMinuteWindow(0, now)
    count = int(row[0])
    minute_started = datetime.fromisoformat(str(row[1]))
    if (now - minute_started) >= timedelta(minutes=1):
        return _ProbeMinuteWindow(0, now)
    return _ProbeMinuteWindow(count, minute_started)


def _persist_probe_minute_window(
    conn: sqlite3.Connection, window: _ProbeMinuteWindow
) -> None:
    conn.execute(
        """
        UPDATE provider_health_metrics
        SET probe_calls_this_minute = ?,
            probe_minute_started_at = ?
        WHERE id = 1
        """,
        (window.count, window.minute_started.isoformat()),
    )


def _record_probe_success(
    conn: sqlite3.Connection,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime,
) -> ProviderProbeExecutionResult:
    row = _fetch_provider_health_row(conn)
    success_count = row.success_count + 1
    breaker_closed = success_count >= policy.success_reset_threshold
    if breaker_closed:
        _persist_provider_health_row(
            conn,
            is_open=False,
            half_open=False,
            failure_count=0,
            success_count=0,
            window_started_at=now,
            opened_at=None,
        )
    else:
        _persist_provider_health_row(
            conn,
            is_open=True,
            half_open=True,
            failure_count=row.failure_count,
            success_count=success_count,
            window_started_at=row.window_started_at,
            opened_at=row.opened_at,
        )
    conn.execute(
        """
        UPDATE provider_health_metrics
        SET probe_success_total = probe_success_total + 1
        WHERE id = 1
        """
    )
    return ProviderProbeExecutionResult(
        executed=True,
        probe_success=True,
        breaker_closed=breaker_closed,
    )


def _record_probe_failure(
    conn: sqlite3.Connection,
    *,
    now: datetime,
) -> ProviderProbeExecutionResult:
    row = _fetch_provider_health_row(conn)
    _persist_provider_health_row(
        conn,
        is_open=True,
        half_open=False,
        failure_count=row.failure_count,
        success_count=0,
        window_started_at=row.window_started_at,
        opened_at=now,
    )
    conn.execute(
        """
        UPDATE provider_health_metrics
        SET probe_failure_total = probe_failure_total + 1
        WHERE id = 1
        """
    )
    return ProviderProbeExecutionResult(
        executed=True,
        probe_success=False,
        breaker_closed=False,
    )


def _increment_production_metric(
    conn: sqlite3.Connection,
    *,
    production_failure: bool,
) -> None:
    column = (
        "production_failure_total"
        if production_failure
        else "production_success_total"
    )
    conn.execute(
        f"""
        UPDATE provider_health_metrics
        SET {column} = {column} + 1
        WHERE id = 1
        """
    )
