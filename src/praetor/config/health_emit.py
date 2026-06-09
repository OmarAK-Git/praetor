"""Durable health-alert outbox with commit-scoped flush queue."""

from __future__ import annotations

import sqlite3

from praetor.alerts.outbox import (
    init_health_alert_outbox_schema,
    write_pending_health_alert,
)
from praetor.contracts.health import SystemHealthAlert
from praetor.hashing.canonical import delimited, sha256_hex
from praetor.state.sqlite_guard import require_critical_transaction

_PENDING_FLUSH_DDL = """
CREATE TABLE IF NOT EXISTS health_alert_pending_flush (
    pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    alert_id TEXT NOT NULL UNIQUE,
    alert_json TEXT NOT NULL,
    flushed INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_health_alert_pending_unflushed
    ON health_alert_pending_flush(flushed, batch_id);
"""


def init_health_alert_emit_schema(conn: sqlite3.Connection) -> None:
    """Ensure outbox + pending-flush tables exist for PolicyGate health alerts."""
    init_health_alert_outbox_schema(conn)
    conn.executescript(_PENDING_FLUSH_DDL)


def stable_health_alert_id(
    *,
    batch_id: str,
    sequence: int,
    alert: SystemHealthAlert,
) -> str:
    """Deterministic alert_id for pending flush idempotency across retries."""
    payload = alert.model_dump_json()
    digest = sha256_hex(
        delimited([batch_id, str(sequence), alert.alert_code, payload])
    )
    return f"hale-{digest[:32]}"


def enqueue_health_alerts_in_transaction(
    conn: sqlite3.Connection,
    alerts: list[SystemHealthAlert],
    *,
    batch_id: str,
) -> list[str]:
    """Queue alerts in the same critical_transaction as state changes."""
    require_critical_transaction(conn)
    alert_ids: list[str] = []
    for sequence, alert in enumerate(alerts):
        alert_id = stable_health_alert_id(
            batch_id=batch_id, sequence=sequence, alert=alert
        )
        alert_ids.append(alert_id)
        conn.execute(
            """
            INSERT INTO health_alert_pending_flush (
                batch_id, alert_id, alert_json, flushed
            ) VALUES (?, ?, ?, 0)
            """,
            (batch_id, alert_id, alert.model_dump_json()),
        )
    return alert_ids


def _flush_pending_row(
    conn: sqlite3.Connection,
    *,
    pending_id: int,
    alert_id: str,
    alert_json: str,
) -> str:
    alert = SystemHealthAlert.model_validate_json(alert_json)
    write_pending_health_alert(conn, alert, alert_id=alert_id)
    conn.execute(
        "UPDATE health_alert_pending_flush SET flushed = 1 WHERE pending_id = ?",
        (pending_id,),
    )
    return alert_id


def flush_health_alert_batch(
    conn: sqlite3.Connection,
    *,
    batch_id: str,
) -> list[str]:
    """Flush queued alerts for one batch to durable outbox."""
    rows = conn.execute(
        """
        SELECT pending_id, alert_id, alert_json FROM health_alert_pending_flush
        WHERE batch_id = ? AND flushed = 0
        ORDER BY pending_id
        """,
        (batch_id,),
    ).fetchall()
    emitted: list[str] = []
    for row in rows:
        emitted.append(
            _flush_pending_row(
                conn,
                pending_id=int(row["pending_id"]),
                alert_id=str(row["alert_id"]),
                alert_json=str(row["alert_json"]),
            )
        )
    return emitted


def drain_unflushed_health_alerts(conn: sqlite3.Connection) -> list[str]:
    """Flush all pending health alerts (recovery after prior partial failure)."""
    rows = conn.execute(
        """
        SELECT pending_id, alert_id, alert_json FROM health_alert_pending_flush
        WHERE flushed = 0
        ORDER BY pending_id
        """
    ).fetchall()
    emitted: list[str] = []
    for row in rows:
        emitted.append(
            _flush_pending_row(
                conn,
                pending_id=int(row["pending_id"]),
                alert_id=str(row["alert_id"]),
                alert_json=str(row["alert_json"]),
            )
        )
    return emitted


def new_health_alert_batch_id() -> str:
    import uuid

    return f"hab-{uuid.uuid4().hex}"
