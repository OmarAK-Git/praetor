"""Containment circuit breaker with sliding-window failures and success reset."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from praetor.config.health_emit import (
    enqueue_health_alerts_in_transaction,
    new_health_alert_batch_id,
)
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.org_config_sections import CircuitBreakerPolicy
from praetor.policy.state import BreakerDomain, init_policy_state_schema
from praetor.state.sqlite_guard import require_critical_transaction

CONTAINMENT_BREAKER_ALERT_CODE = "containment_breaker_open"


@dataclass(frozen=True)
class BreakerTripResult:
    newly_opened: bool
    health_alert_batch_id: str | None = None
    emitted_alert_ids: tuple[str, ...] = ()


def _fetch_breaker_row(
    conn: sqlite3.Connection, domain: BreakerDomain
) -> tuple[int, int, int, str]:
    row = conn.execute(
        """
        SELECT is_open, failure_count, success_count, window_started_at
        FROM circuit_breaker_state
        WHERE domain = ?
        """,
        (domain.value,),
    ).fetchone()
    if row is None:
        msg = f"missing circuit_breaker_state row for {domain.value}"
        raise RuntimeError(msg)
    return int(row[0]), int(row[1]), int(row[2]), str(row[3])


def _advance_breaker_window(
    conn: sqlite3.Connection,
    *,
    domain: BreakerDomain,
    policy: CircuitBreakerPolicy,
    now: datetime,
) -> tuple[int, int, bool]:
    is_open_raw, failure_count, success_count, window_raw = _fetch_breaker_row(
        conn, domain
    )
    is_open = bool(is_open_raw)
    window_started = datetime.fromisoformat(window_raw)
    if (now - window_started).total_seconds() >= float(policy.window_seconds):
        failure_count = 0
        success_count = 0
        is_open = False
        conn.execute(
            """
            UPDATE circuit_breaker_state
            SET failure_count = 0,
                success_count = 0,
                is_open = 0,
                window_started_at = ?
            WHERE domain = ?
            """,
            (now.isoformat(), domain.value),
        )
    return failure_count, success_count, is_open


def is_containment_breaker_open(
    conn: sqlite3.Connection,
    *,
    policy: CircuitBreakerPolicy | None = None,
    now: datetime | None = None,
) -> bool:
    """Return whether containment breaker blocks auto_contain.

    When ``policy`` and ``now`` are supplied, elapsed ``window_seconds`` closes
    the breaker via ``_advance_breaker_window`` (window-based recovery).
    """
    init_policy_state_schema(conn)
    if policy is not None:
        moment = now or datetime.now(UTC)
        _, _, is_open = _advance_breaker_window(
            conn,
            domain=BreakerDomain.CONTAINMENT,
            policy=policy,
            now=moment,
        )
        return is_open
    row = conn.execute(
        "SELECT is_open FROM circuit_breaker_state WHERE domain = ?",
        (BreakerDomain.CONTAINMENT.value,),
    ).fetchone()
    if row is None:
        return False
    return bool(int(row[0]))


def record_rate_limit_failure_in_transaction(
    conn: sqlite3.Connection,
    *,
    policy: CircuitBreakerPolicy,
    now: datetime | None = None,
) -> BreakerTripResult:
    """Record rate-limit failure; trip breaker and enqueue alert at threshold."""
    require_critical_transaction(conn)
    moment = now or datetime.now(UTC)
    failure_count, success_count, is_open = _advance_breaker_window(
        conn,
        domain=BreakerDomain.CONTAINMENT,
        policy=policy,
        now=moment,
    )
    failure_count += 1
    success_count = 0
    newly_opened = False
    batch_id: str | None = None
    emitted: list[str] = []

    if failure_count >= policy.failure_threshold and not is_open:
        newly_opened = True
        is_open = True
        batch_id = new_health_alert_batch_id()
        alert = SystemHealthAlert(
            alert_code=CONTAINMENT_BREAKER_ALERT_CODE,
            emitted_at=moment,
        )
        emitted = enqueue_health_alerts_in_transaction(
            conn, [alert], batch_id=batch_id
        )

    conn.execute(
        """
        UPDATE circuit_breaker_state
        SET is_open = ?, failure_count = ?, success_count = ?
        WHERE domain = ?
        """,
        (
            1 if is_open else 0,
            failure_count,
            success_count,
            BreakerDomain.CONTAINMENT.value,
        ),
    )

    return BreakerTripResult(
        newly_opened=newly_opened,
        health_alert_batch_id=batch_id,
        emitted_alert_ids=tuple(emitted),
    )


def record_containment_success_in_transaction(
    conn: sqlite3.Connection,
    *,
    policy: CircuitBreakerPolicy,
    now: datetime | None = None,
) -> bool:
    """Record containment success; reset failure state at success threshold."""
    require_critical_transaction(conn)
    moment = now or datetime.now(UTC)
    failure_count, success_count, is_open = _advance_breaker_window(
        conn,
        domain=BreakerDomain.CONTAINMENT,
        policy=policy,
        now=moment,
    )
    if is_open:
        return False

    success_count += 1
    reset = success_count >= policy.success_reset_threshold
    if reset:
        failure_count = 0
        success_count = 0

    conn.execute(
        """
        UPDATE circuit_breaker_state
        SET failure_count = ?, success_count = ?
        WHERE domain = ?
        """,
        (
            failure_count,
            success_count,
            BreakerDomain.CONTAINMENT.value,
        ),
    )
    return reset
