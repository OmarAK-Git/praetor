"""Revocation feed outbox helpers and export metadata (Task 11)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

_EXPORT_META_DDL = """
CREATE TABLE IF NOT EXISTS revocation_feed_export_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_verified_exported_sequence INTEGER NOT NULL DEFAULT 0,
    feed_unhealthy INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO revocation_feed_export_meta (
    id, last_verified_exported_sequence, feed_unhealthy
) VALUES (1, 0, 0);
"""


class FeedOutboxStatus(StrEnum):
    PENDING = "pending"
    EXPORTED = "exported"


@dataclass(frozen=True)
class FeedOutboxRow:
    sequence_number: int
    revocation_id: str
    directive_id: str
    status: FeedOutboxStatus
    created_at: datetime
    export_retry_count: int


def _outbox_columns(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(revocation_feed_outbox)").fetchall()
    }


def _migrate_outbox_schema(conn: sqlite3.Connection) -> None:
    cols = _outbox_columns(conn)
    if cols and "export_retry_count" not in cols:
        conn.execute(
            """
            ALTER TABLE revocation_feed_outbox
            ADD COLUMN export_retry_count INTEGER NOT NULL DEFAULT 0
            """
        )


def init_revocation_feed_export_schema(conn: sqlite3.Connection) -> None:
    """Additive export metadata and outbox retry column."""
    conn.execute("PRAGMA foreign_keys=ON")
    _migrate_outbox_schema(conn)
    conn.executescript(_EXPORT_META_DDL)


def _row_to_outbox(row: sqlite3.Row) -> FeedOutboxRow:
    created_at = datetime.fromisoformat(str(row["created_at"]))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return FeedOutboxRow(
        sequence_number=int(row["sequence_number"]),
        revocation_id=str(row["revocation_id"]),
        directive_id=str(row["directive_id"]),
        status=FeedOutboxStatus(str(row["status"])),
        created_at=created_at,
        export_retry_count=int(row["export_retry_count"]),
    )


def fetch_feed_outbox_row_extended(
    conn: sqlite3.Connection, sequence_number: int
) -> FeedOutboxRow | None:
    row = conn.execute(
        """
        SELECT sequence_number, revocation_id, directive_id, status,
               created_at, export_retry_count
        FROM revocation_feed_outbox
        WHERE sequence_number = ?
        """,
        (sequence_number,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_outbox(row)


def list_pending_feed_outbox_rows(conn: sqlite3.Connection) -> list[FeedOutboxRow]:
    rows = conn.execute(
        """
        SELECT sequence_number, revocation_id, directive_id, status,
               created_at, export_retry_count
        FROM revocation_feed_outbox
        WHERE status = ?
        ORDER BY sequence_number ASC
        """,
        (FeedOutboxStatus.PENDING.value,),
    ).fetchall()
    return [_row_to_outbox(row) for row in rows]


def read_last_verified_exported_sequence(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT last_verified_exported_sequence
        FROM revocation_feed_export_meta WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def is_feed_unhealthy(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT feed_unhealthy FROM revocation_feed_export_meta WHERE id = 1"
    ).fetchone()
    if row is None:
        return False
    return bool(int(row[0]))


def set_feed_unhealthy(conn: sqlite3.Connection, *, unhealthy: bool) -> None:
    conn.execute(
        """
        UPDATE revocation_feed_export_meta
        SET feed_unhealthy = ?
        WHERE id = 1
        """,
        (1 if unhealthy else 0,),
    )


def mark_feed_row_exported(
    conn: sqlite3.Connection, *, sequence_number: int
) -> None:
    conn.execute(
        """
        UPDATE revocation_feed_outbox
        SET status = ?
        WHERE sequence_number = ?
        """,
        (FeedOutboxStatus.EXPORTED.value, sequence_number),
    )
    conn.execute(
        """
        UPDATE revocation_feed_export_meta
        SET last_verified_exported_sequence = ?
        WHERE id = 1
        """,
        (sequence_number,),
    )


def increment_feed_export_retry(
    conn: sqlite3.Connection, *, sequence_number: int
) -> int:
    conn.execute(
        """
        UPDATE revocation_feed_outbox
        SET export_retry_count = export_retry_count + 1
        WHERE sequence_number = ?
        """,
        (sequence_number,),
    )
    row = conn.execute(
        """
        SELECT export_retry_count FROM revocation_feed_outbox
        WHERE sequence_number = ?
        """,
        (sequence_number,),
    ).fetchone()
    if row is None:
        msg = f"feed outbox row missing: {sequence_number}"
        raise RuntimeError(msg)
    return int(row[0])


def oldest_pending_feed_age_seconds(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> float | None:
    """Age of oldest pending row from ``ledger_commit_at`` (PolicyGate probe)."""
    row = conn.execute(
        """
        SELECT MIN(r.ledger_commit_at) AS oldest_commit
        FROM revocation_feed_outbox o
        JOIN directive_revocation_records r
          ON r.revocation_id = o.revocation_id
        WHERE o.status = ?
        """,
        (FeedOutboxStatus.PENDING.value,),
    ).fetchone()
    if row is None or row["oldest_commit"] is None:
        return None
    commit_at = datetime.fromisoformat(str(row["oldest_commit"]))
    if commit_at.tzinfo is None:
        commit_at = commit_at.replace(tzinfo=UTC)
    reference = now if now is not None else datetime.now(UTC)
    return (reference - commit_at).total_seconds()


def has_feed_sequence_gap(conn: sqlite3.Connection) -> bool:
    """True when a pending row exists beyond a missing next sequence."""
    last_verified = read_last_verified_exported_sequence(conn)
    next_expected = last_verified + 1
    if fetch_feed_outbox_row_extended(conn, next_expected) is not None:
        return False
    for row in list_pending_feed_outbox_rows(conn):
        if row.sequence_number > next_expected:
            return True
    return False


def fetch_ledger_commit_at(
    conn: sqlite3.Connection, revocation_id: str
) -> datetime | None:
    row = conn.execute(
        """
        SELECT ledger_commit_at FROM directive_revocation_records
        WHERE revocation_id = ?
        """,
        (revocation_id,),
    ).fetchone()
    if row is None:
        return None
    commit_at = datetime.fromisoformat(str(row["ledger_commit_at"]))
    if commit_at.tzinfo is None:
        commit_at = commit_at.replace(tzinfo=UTC)
    return commit_at

