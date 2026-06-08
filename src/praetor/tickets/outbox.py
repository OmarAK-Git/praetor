"""Durable SQLite ticket stamp outbox."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from praetor.state.sqlite_guard import critical_transaction

_STAMP_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS ticket_stamp_outbox (
    stamp_id TEXT PRIMARY KEY,
    alert_identity TEXT NOT NULL,
    evidence_bundle_hash TEXT NOT NULL,
    org_config_snapshot_hash TEXT NOT NULL,
    processing_attempt_identity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    ticket_payload_json TEXT NOT NULL,
    response_payload_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_initialized_conn_ids: set[int] = set()


def _stamp_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'ticket_stamp_outbox'
        """
    ).fetchone()
    return row is not None


class StampStatus(StrEnum):
    """Durable stamp outcome; unknown is distinct from failed (docs/plan.md Task 7)."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


TERMINAL_STAMP_STATUSES = frozenset(
    {StampStatus.SUCCEEDED, StampStatus.FAILED, StampStatus.UNKNOWN}
)


@dataclass(frozen=True)
class StampOutboxEntry:
    stamp_id: str
    alert_identity: str
    evidence_bundle_hash: str
    org_config_snapshot_hash: str
    processing_attempt_identity: str
    status: StampStatus
    ticket_payload: dict[str, Any]
    response_payload: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


def ensure_stamp_outbox_schema(conn: sqlite3.Connection) -> None:
    """Create stamp outbox table if missing (additive Task 7 schema).

    Per-connection cache avoids repeated DDL after ``init_stamp_outbox_schema`` at
    open; cache misses when SQLite reuses a recycled ``id(conn)`` for a new handle.
    """
    conn_id = id(conn)
    if conn_id in _initialized_conn_ids and _stamp_table_exists(conn):
        return
    if conn_id in _initialized_conn_ids:
        _initialized_conn_ids.discard(conn_id)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_STAMP_OUTBOX_DDL)
    _initialized_conn_ids.add(conn_id)


def init_stamp_outbox_schema(conn: sqlite3.Connection) -> None:
    """Alias for store open hook."""
    ensure_stamp_outbox_schema(conn)


def _row_to_entry(row: sqlite3.Row) -> StampOutboxEntry:
    created_at = datetime.fromisoformat(str(row["created_at"]))
    updated_at = datetime.fromisoformat(str(row["updated_at"]))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    response_raw = row["response_payload_json"]
    response_payload = (
        json.loads(str(response_raw)) if response_raw is not None else None
    )
    return StampOutboxEntry(
        stamp_id=str(row["stamp_id"]),
        alert_identity=str(row["alert_identity"]),
        evidence_bundle_hash=str(row["evidence_bundle_hash"]),
        org_config_snapshot_hash=str(row["org_config_snapshot_hash"]),
        processing_attempt_identity=str(row["processing_attempt_identity"]),
        status=StampStatus(str(row["status"])),
        ticket_payload=json.loads(str(row["ticket_payload_json"])),
        response_payload=response_payload,
        created_at=created_at,
        updated_at=updated_at,
    )


def fetch_stamp_outbox(
    conn: sqlite3.Connection, stamp_id: str
) -> StampOutboxEntry | None:
    ensure_stamp_outbox_schema(conn)
    row = conn.execute(
        """
        SELECT stamp_id, alert_identity, evidence_bundle_hash,
               org_config_snapshot_hash, processing_attempt_identity,
               status, ticket_payload_json, response_payload_json,
               created_at, updated_at
        FROM ticket_stamp_outbox
        WHERE stamp_id = ?
        """,
        (stamp_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_entry(row)


def write_pending_stamp(
    conn: sqlite3.Connection,
    *,
    stamp_id: str,
    alert_identity: str,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    processing_attempt_identity: str,
    ticket_payload: dict[str, Any],
) -> StampOutboxEntry:
    """Persist pending outbox row before any external ticket call."""
    ensure_stamp_outbox_schema(conn)
    now = datetime.now(UTC).isoformat()
    payload_json = json.dumps(ticket_payload, sort_keys=True, separators=(",", ":"))
    with critical_transaction(conn):
        conn.execute(
            """
            INSERT INTO ticket_stamp_outbox (
                stamp_id, alert_identity, evidence_bundle_hash,
                org_config_snapshot_hash, processing_attempt_identity,
                status, ticket_payload_json, response_payload_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                stamp_id,
                alert_identity,
                evidence_bundle_hash,
                org_config_snapshot_hash,
                processing_attempt_identity,
                StampStatus.PENDING.value,
                payload_json,
                now,
                now,
            ),
        )
    entry = fetch_stamp_outbox(conn, stamp_id)
    assert entry is not None
    return entry


def record_stamp_outcome(
    conn: sqlite3.Connection,
    stamp_id: str,
    status: StampStatus,
    response_payload: dict[str, Any] | None,
) -> StampOutboxEntry:
    """Record definite or ambiguous stamp outcome durably."""
    if status == StampStatus.PENDING:
        msg = "record_stamp_outcome requires a terminal or unknown status"
        raise ValueError(msg)
    ensure_stamp_outbox_schema(conn)
    now = datetime.now(UTC).isoformat()
    response_json = (
        json.dumps(response_payload, sort_keys=True, separators=(",", ":"))
        if response_payload is not None
        else None
    )
    with critical_transaction(conn):
        updated = conn.execute(
            """
            UPDATE ticket_stamp_outbox
            SET status = ?, response_payload_json = ?, updated_at = ?
            WHERE stamp_id = ?
            """,
            (status.value, response_json, now, stamp_id),
        )
        if updated.rowcount != 1:
            msg = f"stamp outbox row not found: {stamp_id!r}"
            raise KeyError(msg)
    entry = fetch_stamp_outbox(conn, stamp_id)
    assert entry is not None
    return entry
