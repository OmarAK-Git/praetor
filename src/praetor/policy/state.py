"""PolicyGate durable state: rate counters, breakers, startup reconciliation."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from praetor.config.state import fetch_outstanding_unrevoked_directives
from praetor.contracts.containment import ContainmentDirective
from praetor.hashing import derive_idempotency_key
from praetor.state.idempotency import (
    fetch_active_idempotency_key,
    insert_active_idempotency_key,
)
from praetor.state.sqlite_guard import StartupGuardError, critical_transaction

_POLICY_STATE_DDL = """
CREATE TABLE IF NOT EXISTS containment_rate_counters (
    scope_key TEXT PRIMARY KEY,
    event_count INTEGER NOT NULL,
    window_started_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    domain TEXT PRIMARY KEY CHECK (domain IN ('containment', 'provider_health')),
    is_open INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    window_started_at TEXT NOT NULL
);

INSERT OR IGNORE INTO circuit_breaker_state (
    domain, is_open, failure_count, success_count, window_started_at
) VALUES ('containment', 0, 0, 0, '1970-01-01T00:00:00+00:00');

INSERT OR IGNORE INTO circuit_breaker_state (
    domain, is_open, failure_count, success_count, window_started_at
) VALUES ('provider_health', 0, 0, 0, '1970-01-01T00:00:00+00:00');
"""

REQUIRED_PRODUCTION_POLICY_TABLES = frozenset(
    {
        "analyst_annotations",
        "containment_rate_counters",
        "circuit_breaker_state",
        "policy_gate_evaluations",
        "provider_health_metrics",
        "revocation_feed_export_meta",
    }
)

# Task 17 uses a fixed per-scope ceiling until Task 18 adds org-config limits.
_V1_DEFAULT_SCOPE_LIMIT = 1


class BreakerDomain(StrEnum):
    CONTAINMENT = "containment"
    PROVIDER_HEALTH = "provider_health"


@dataclass(frozen=True)
class PolicyStateReconciliationResult:
    idempotency_keys_registered: int
    rate_counters_reset: bool
    breakers_reconciled: int


def init_policy_state_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_POLICY_STATE_DDL)


def _existing_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def ensure_production_policy_tables(conn: sqlite3.Connection) -> None:
    """Create or upgrade policy tables required for production startup."""
    init_policy_state_schema(conn)
    from praetor.judgment.provider_health_breaker import (
        init_provider_health_breaker_schema,
    )
    from praetor.metrics.evaluations import init_policy_gate_evaluation_schema

    init_provider_health_breaker_schema(conn)
    init_policy_gate_evaluation_schema(conn)


def assert_production_policy_tables(conn: sqlite3.Connection) -> None:
    """Fail closed when required production policy tables are missing."""
    missing = REQUIRED_PRODUCTION_POLICY_TABLES - _existing_table_names(conn)
    if missing:
        names = ", ".join(sorted(missing))
        msg = f"production startup missing required policy tables: {names}"
        raise StartupGuardError(msg)


def rate_limit_scope_key(scope: str, *, target_type: str, target_id: str) -> str:
    from praetor.policy.rate_limit import rate_limit_scope_key as _key

    return _key(scope, target_type=target_type, target_id=target_id)


def read_rate_counter(conn: sqlite3.Connection, scope_key: str) -> int:
    row = conn.execute(
        "SELECT event_count FROM containment_rate_counters WHERE scope_key = ?",
        (scope_key,),
    ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def set_rate_counter(conn: sqlite3.Connection, scope_key: str, count: int) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO containment_rate_counters (
            scope_key, event_count, window_started_at
        )
        VALUES (?, ?, ?)
        ON CONFLICT(scope_key) DO UPDATE SET
            event_count = excluded.event_count,
            window_started_at = excluded.window_started_at
        """,
        (scope_key, count, now),
    )


def increment_rate_counter_in_transaction(
    conn: sqlite3.Connection,
    scope_key: str,
) -> int:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO containment_rate_counters (
            scope_key, event_count, window_started_at
        )
        VALUES (?, 1, ?)
        ON CONFLICT(scope_key) DO UPDATE SET
            event_count = event_count + 1,
            window_started_at = excluded.window_started_at
        """,
        (scope_key, now),
    )
    return read_rate_counter(conn, scope_key)


def is_rate_limit_exceeded(
    conn: sqlite3.Connection,
    *,
    scope_key: str,
    limit: int = _V1_DEFAULT_SCOPE_LIMIT,
) -> bool:
    """Legacy single-scope check; prefer is_rate_limit_exceeded_for_target."""
    return read_rate_counter(conn, scope_key) >= limit


def is_breaker_open(conn: sqlite3.Connection, domain: BreakerDomain) -> bool:
    row = conn.execute(
        "SELECT is_open FROM circuit_breaker_state WHERE domain = ?",
        (domain.value,),
    ).fetchone()
    if row is None:
        return False
    return bool(int(row[0]))


def set_breaker_open(
    conn: sqlite3.Connection,
    domain: BreakerDomain,
    *,
    open_: bool,
) -> None:
    conn.execute(
        "UPDATE circuit_breaker_state SET is_open = ? WHERE domain = ?",
        (1 if open_ else 0, domain.value),
    )


def _register_idempotency_for_directive(
    conn: sqlite3.Connection,
    directive: ContainmentDirective,
    *,
    alert_identity: str,
) -> bool:
    key = derive_idempotency_key(
        alert_identity,
        directive.target_type.value,
        directive.target_id,
        directive.scope,
    )
    if fetch_active_idempotency_key(conn, key) is not None:
        return False
    try:
        insert_active_idempotency_key(
            conn,
            idempotency_key=key,
            alert_identity=alert_identity,
            target_type=directive.target_type.value,
            target_id=directive.target_id,
            scope=directive.scope,
        )
    except Exception:
        return False
    return True


def reconcile_policy_state(conn: sqlite3.Connection) -> PolicyStateReconciliationResult:
    """Startup step 6: align idempotency keys and policy counters with durable state."""
    ensure_production_policy_tables(conn)
    registered = 0
    with critical_transaction(conn):
        conn.execute("DELETE FROM containment_rate_counters")
        for directive in fetch_outstanding_unrevoked_directives(conn):
            alert_identity = _alert_identity_for_directive(conn, directive)
            if alert_identity is None:
                continue
            if _register_idempotency_for_directive(
                conn, directive, alert_identity=alert_identity
            ):
                registered += 1
        breakers = conn.execute("SELECT COUNT(*) FROM circuit_breaker_state").fetchone()
    return PolicyStateReconciliationResult(
        idempotency_keys_registered=registered,
        rate_counters_reset=True,
        breakers_reconciled=int(breakers[0]) if breakers else 0,
    )


def _alert_identity_for_directive(
    conn: sqlite3.Connection,
    directive: ContainmentDirective,
) -> str | None:
    row = conn.execute(
        """
        SELECT json_extract(record_json, '$.alert_reference') AS alert_reference
        FROM ledger_chain
        WHERE record_type = 'decision_edict'
          AND json_extract(record_json, '$.decision_id') = ?
        LIMIT 1
        """,
        (directive.decision_id,),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])


def directive_has_ledger_edict(conn: sqlite3.Connection, decision_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM ledger_chain
        WHERE record_type = 'decision_edict'
          AND json_extract(record_json, '$.decision_id') = ?
        LIMIT 1
        """,
        (decision_id,),
    ).fetchone()
    return row is not None


def fetch_orphan_outstanding_directives(
    conn: sqlite3.Connection,
) -> list[ContainmentDirective]:
    """Outstanding directives with no matching ledger DecisionEdict (DEC-060)."""
    return [
        directive
        for directive in fetch_outstanding_unrevoked_directives(conn)
        if not directive_has_ledger_edict(conn, directive.decision_id)
    ]
