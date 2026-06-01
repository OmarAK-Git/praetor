"""Durable SQLite SystemHealthAlert outbox.

See ``docs/spec.md`` § SystemHealthAlert Delivery.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from praetor.contracts.health import SystemHealthAlert
from praetor.state.sqlite_guard import critical_transaction

_HEALTH_ALERT_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS system_health_alert_outbox (
    alert_id TEXT PRIMARY KEY,
    alert_code TEXT NOT NULL,
    alert_payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_health_delivery_attempts (
    alert_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempted_at TEXT,
    result_json TEXT,
    PRIMARY KEY (alert_id, channel),
    FOREIGN KEY (alert_id) REFERENCES system_health_alert_outbox(alert_id)
);
"""

_initialized_conn_ids: set[int] = set()
# v1 single-process/single-writer: one guarded connection per open store for the
# process lifetime. Cache avoids repeated DDL; safe because connections are not
# pooled or recycled across unrelated handles in v1. Revisit if multi-connection
# refactors land (invalidate on close or key by db path + conn identity).

V1_DELIVERY_CHANNELS = frozenset({"jsonl", "stdout"})


def _health_alert_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'system_health_alert_outbox'
        """
    ).fetchone()
    return row is not None


class DeliveryStatus(StrEnum):
    """Per-channel delivery outcome."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DuplicateHealthAlertError(Exception):
    """Raised when the same ``alert_id`` is reused with a different payload."""


@dataclass(frozen=True)
class HealthAlertOutboxEntry:
    alert_id: str
    alert: SystemHealthAlert
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DeliveryAttempt:
    alert_id: str
    channel: str
    status: DeliveryStatus
    attempted_at: datetime | None
    result: dict[str, Any] | None


def ensure_health_alert_outbox_schema(conn: sqlite3.Connection) -> None:
    """Create health alert outbox tables if missing (additive Task 8 schema)."""
    conn_id = id(conn)
    if conn_id in _initialized_conn_ids and _health_alert_table_exists(conn):
        return
    if conn_id in _initialized_conn_ids:
        _initialized_conn_ids.discard(conn_id)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_HEALTH_ALERT_OUTBOX_DDL)
    _initialized_conn_ids.add(conn_id)


def init_health_alert_outbox_schema(conn: sqlite3.Connection) -> None:
    """Alias for store open hook."""
    ensure_health_alert_outbox_schema(conn)


def _row_to_outbox_entry(row: sqlite3.Row) -> HealthAlertOutboxEntry:
    created_at = datetime.fromisoformat(str(row["created_at"]))
    updated_at = datetime.fromisoformat(str(row["updated_at"]))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    alert = SystemHealthAlert.model_validate_json(str(row["alert_payload_json"]))
    return HealthAlertOutboxEntry(
        alert_id=str(row["alert_id"]),
        alert=alert,
        created_at=created_at,
        updated_at=updated_at,
    )


def _row_to_delivery_attempt(row: sqlite3.Row) -> DeliveryAttempt:
    attempted_raw = row["attempted_at"]
    attempted_at: datetime | None
    if attempted_raw is None:
        attempted_at = None
    else:
        attempted_at = datetime.fromisoformat(str(attempted_raw))
        if attempted_at.tzinfo is None:
            attempted_at = attempted_at.replace(tzinfo=UTC)
    result_raw = row["result_json"]
    result = json.loads(str(result_raw)) if result_raw is not None else None
    return DeliveryAttempt(
        alert_id=str(row["alert_id"]),
        channel=str(row["channel"]),
        status=DeliveryStatus(str(row["status"])),
        attempted_at=attempted_at,
        result=result,
    )


def fetch_health_alert_outbox(
    conn: sqlite3.Connection, alert_id: str
) -> HealthAlertOutboxEntry | None:
    ensure_health_alert_outbox_schema(conn)
    row = conn.execute(
        """
        SELECT alert_id, alert_code, alert_payload_json, created_at, updated_at
        FROM system_health_alert_outbox
        WHERE alert_id = ?
        """,
        (alert_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_outbox_entry(row)


def fetch_delivery_attempt(
    conn: sqlite3.Connection, alert_id: str, channel: str
) -> DeliveryAttempt | None:
    ensure_health_alert_outbox_schema(conn)
    row = conn.execute(
        """
        SELECT alert_id, channel, status, attempted_at, result_json
        FROM system_health_delivery_attempts
        WHERE alert_id = ? AND channel = ?
        """,
        (alert_id, channel),
    ).fetchone()
    if row is None:
        return None
    return _row_to_delivery_attempt(row)


def write_pending_health_alert(
    conn: sqlite3.Connection,
    alert: SystemHealthAlert,
    *,
    alert_id: str | None = None,
) -> HealthAlertOutboxEntry:
    """Persist alert and pending delivery rows before any external delivery.

    Duplicate ``alert_id`` with an identical payload is idempotent (returns the
    existing row). Duplicate ``alert_id`` with a different payload raises
    ``DuplicateHealthAlertError``.
    """
    ensure_health_alert_outbox_schema(conn)
    resolved_alert_id = alert_id or str(uuid.uuid4())
    payload_json = alert.model_dump_json()
    now = datetime.now(UTC).isoformat()
    with critical_transaction(conn):
        # Existence check inside BEGIN IMMEDIATE: v1 single-writer (OS singleton +
        # one process) serializes concurrent persist; revisit if multi-writer lands.
        existing = fetch_health_alert_outbox(conn, resolved_alert_id)
        if existing is not None:
            if existing.alert.model_dump_json() == payload_json:
                return existing
            msg = f"health alert id conflict: {resolved_alert_id!r}"
            raise DuplicateHealthAlertError(msg)
        conn.execute(
            """
            INSERT INTO system_health_alert_outbox (
                alert_id, alert_code, alert_payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                resolved_alert_id,
                alert.alert_code,
                payload_json,
                now,
                now,
            ),
        )
        for channel in sorted(V1_DELIVERY_CHANNELS):
            conn.execute(
                """
                INSERT INTO system_health_delivery_attempts (
                    alert_id, channel, status, attempted_at, result_json
                ) VALUES (?, ?, ?, NULL, NULL)
                """,
                (resolved_alert_id, channel, DeliveryStatus.PENDING.value),
            )
    entry = fetch_health_alert_outbox(conn, resolved_alert_id)
    assert entry is not None
    return entry


def record_delivery_attempt(
    conn: sqlite3.Connection,
    alert_id: str,
    channel: str,
    status: DeliveryStatus,
    result: dict[str, Any] | None,
) -> DeliveryAttempt:
    """Record delivery attempt timestamp and result for a channel."""
    if status == DeliveryStatus.PENDING:
        msg = "record_delivery_attempt requires succeeded or failed status"
        raise ValueError(msg)
    ensure_health_alert_outbox_schema(conn)
    now = datetime.now(UTC).isoformat()
    result_json = (
        json.dumps(result, sort_keys=True, separators=(",", ":"))
        if result is not None
        else None
    )
    with critical_transaction(conn):
        updated = conn.execute(
            """
            UPDATE system_health_delivery_attempts
            SET status = ?, attempted_at = ?, result_json = ?
            WHERE alert_id = ? AND channel = ?
            """,
            (status.value, now, result_json, alert_id, channel),
        )
        if updated.rowcount != 1:
            msg = f"delivery attempt not found: {alert_id!r} / {channel!r}"
            raise KeyError(msg)
        conn.execute(
            """
            UPDATE system_health_alert_outbox
            SET updated_at = ?
            WHERE alert_id = ?
            """,
            (now, alert_id),
        )
    attempt = fetch_delivery_attempt(conn, alert_id, channel)
    assert attempt is not None
    return attempt


def fetch_retryable_delivery_attempts(
    conn: sqlite3.Connection,
) -> list[tuple[HealthAlertOutboxEntry, DeliveryAttempt]]:
    """Return outbox entries with at least one pending or failed channel attempt."""
    ensure_health_alert_outbox_schema(conn)
    rows = conn.execute(
        """
        SELECT o.alert_id, o.alert_code, o.alert_payload_json,
               o.created_at, o.updated_at,
               d.channel, d.status, d.attempted_at, d.result_json
        FROM system_health_alert_outbox o
        JOIN system_health_delivery_attempts d ON d.alert_id = o.alert_id
        WHERE d.status IN (?, ?)
        ORDER BY o.created_at, d.channel
        """,
        (DeliveryStatus.PENDING.value, DeliveryStatus.FAILED.value),
    ).fetchall()
    seen: set[tuple[str, str]] = set()
    results: list[tuple[HealthAlertOutboxEntry, DeliveryAttempt]] = []
    for row in rows:
        key = (str(row["alert_id"]), str(row["channel"]))
        if key in seen:
            continue
        seen.add(key)
        entry = _row_to_outbox_entry(row)
        attempt = _row_to_delivery_attempt(row)
        results.append((entry, attempt))
    return results
