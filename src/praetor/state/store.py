"""SQLite state store — authoritative attempt lifecycle (v1 single-writer).

Deployment constraint (docs/plan.md Task 6): one Praetor process holds the OS
singleton lock (Task 5 ``SingletonLock``) and performs all critical SQLite writes.
``open_state_store`` does not acquire the singleton; callers must hold the lock
before opening the store in production. Concurrent writers are unsupported;
BEGIN IMMEDIATE serializes allocation and revocation paths.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.state.attempts import (
    AllocationResult,
    ProcessingAttempt,
    allocate_attempt,
)
from praetor.state.idempotency import (
    clear_idempotency_key,
    fetch_active_idempotency_key,
    insert_active_idempotency_key,
)
from praetor.state.sqlite_guard import (
    create_guarded_connection,
    critical_transaction,
    init_state_dir,
)

SCHEMA_VERSION = 1
SCHEMA_VERSION_KEY = "schema_version"


class IncompatibleSchemaError(Exception):
    """Raised when an existing state DB schema version does not match this build."""

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_identity TEXT NOT NULL,
    evidence_bundle_hash TEXT NOT NULL,
    org_config_snapshot_hash TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_non_terminal_per_alert
    ON processing_attempts(alert_identity)
    WHERE state NOT IN ('completed', 'aborted');

CREATE TABLE IF NOT EXISTS completed_decisions (
    alert_identity TEXT NOT NULL,
    evidence_bundle_hash TEXT NOT NULL,
    org_config_snapshot_hash TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    processing_attempt_identity TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (
        alert_identity, evidence_bundle_hash, org_config_snapshot_hash
    )
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    alert_identity TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    created_at TEXT NOT NULL,
    cleared_at TEXT
);

CREATE TABLE IF NOT EXISTS directive_revocation_records (
    revocation_id TEXT PRIMARY KEY,
    directive_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    ledger_commit_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revocation_feed_outbox (
    sequence_number INTEGER PRIMARY KEY,
    revocation_id TEXT NOT NULL UNIQUE,
    directive_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (revocation_id) REFERENCES directive_revocation_records(revocation_id)
);

CREATE TABLE IF NOT EXISTS revocation_feed_sequence (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    next_sequence INTEGER NOT NULL
);

INSERT OR IGNORE INTO revocation_feed_sequence (id, next_sequence) VALUES (1, 1);
"""


@dataclass
class RevocationWriteResult:
    record: DirectiveRevocationRecord
    sequence_number: int


@dataclass
class StateStore:
    """Opened state database connection with initialized schema."""

    conn: sqlite3.Connection
    db_path: Path

    def allocate_attempt(
        self,
        *,
        alert_identity: str,
        evidence_bundle_hash: str,
        org_config_snapshot_hash: str,
    ) -> AllocationResult:
        return allocate_attempt(
            self.conn,
            alert_identity=alert_identity,
            evidence_bundle_hash=evidence_bundle_hash,
            org_config_snapshot_hash=org_config_snapshot_hash,
        )

    def register_idempotency_key(
        self,
        *,
        idempotency_key: str,
        alert_identity: str,
        target_type: str,
        target_id: str,
        scope: str,
    ) -> None:
        with critical_transaction(self.conn):
            insert_active_idempotency_key(
                self.conn,
                idempotency_key=idempotency_key,
                alert_identity=alert_identity,
                target_type=target_type,
                target_id=target_id,
                scope=scope,
            )

    def write_manual_revocation(
        self,
        record: DirectiveRevocationRecord,
        *,
        idempotency_key: str,
    ) -> RevocationWriteResult:
        """SOC-lead manual revocation: record, feed outbox, clear idempotency key."""
        if record.reason != RevocationReason.MANUAL:
            msg = "write_manual_revocation requires reason=manual"
            raise ValueError(msg)
        if not record.idempotency_key_cleared:
            msg = "manual revocation must set idempotency_key_cleared=true"
            raise ValueError(msg)
        return self._write_revocation(
            record, clear_idempotency_key_value=idempotency_key
        )

    def write_automated_revocation(
        self, record: DirectiveRevocationRecord
    ) -> RevocationWriteResult:
        """Automated revocation: record and feed outbox; idempotency key unchanged."""
        if record.idempotency_key_cleared:
            msg = "automated revocation must not clear idempotency key"
            raise ValueError(msg)
        if record.reason == RevocationReason.MANUAL:
            msg = "automated path cannot use reason=manual"
            raise ValueError(msg)
        return self._write_revocation(record, clear_idempotency_key_value=None)

    def _write_revocation(
        self,
        record: DirectiveRevocationRecord,
        *,
        clear_idempotency_key_value: str | None,
    ) -> RevocationWriteResult:
        with critical_transaction(self.conn):
            sequence_number = _next_feed_sequence(self.conn)
            record_json = record.model_dump_json()
            self.conn.execute(
                """
                INSERT INTO directive_revocation_records (
                    revocation_id, directive_id, record_json, ledger_commit_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    record.revocation_id,
                    record.directive_id,
                    record_json,
                    record.ledger_commit_at.isoformat(),
                ),
            )
            created_at = datetime.now(UTC).isoformat()
            self.conn.execute(
                """
                INSERT INTO revocation_feed_outbox (
                    sequence_number, revocation_id, directive_id, status, created_at
                ) VALUES (?, ?, ?, 'pending', ?)
                """,
                (
                    sequence_number,
                    record.revocation_id,
                    record.directive_id,
                    created_at,
                ),
            )
            if clear_idempotency_key_value is not None:
                clear_idempotency_key(self.conn, clear_idempotency_key_value)
            return RevocationWriteResult(record=record, sequence_number=sequence_number)

    def close(self) -> None:
        self.conn.close()


def _next_feed_sequence(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT next_sequence FROM revocation_feed_sequence WHERE id = 1"
    ).fetchone()
    if row is None:
        msg = "revocation_feed_sequence not initialized"
        raise RuntimeError(msg)
    seq = int(row[0])
    conn.execute(
        "UPDATE revocation_feed_sequence SET next_sequence = ? WHERE id = 1",
        (seq + 1,),
    )
    return seq


def _read_schema_version(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (SCHEMA_VERSION_KEY,),
    ).fetchone()
    if row is None:
        return None
    return int(row[0])


def verify_schema_version(conn: sqlite3.Connection) -> None:
    """Reject databases written by an incompatible schema version."""
    stored = _read_schema_version(conn)
    if stored is None:
        return
    if stored != SCHEMA_VERSION:
        msg = (
            f"incompatible state schema: stored version {stored}, "
            f"expected {SCHEMA_VERSION}"
        )
        raise IncompatibleSchemaError(msg)


def init_state_schema(conn: sqlite3.Connection) -> None:
    """Create Task 6 tables if missing and pin schema version on first init."""
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA_SQL)
    stored = _read_schema_version(conn)
    if stored is None:
        conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES (?, ?)",
            (SCHEMA_VERSION_KEY, str(SCHEMA_VERSION)),
        )
    else:
        verify_schema_version(conn)


def open_state_store(db_path: Path) -> StateStore:
    """Bootstrap WAL, open guarded connection, verify schema, initialize if new.

    Does not acquire the Task 5 singleton lock; production callers must hold
    ``SingletonLock`` for the state directory before calling this function.
    """
    init_state_dir(db_path)
    conn = create_guarded_connection(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA_SQL)
    verify_schema_version(conn)
    stored = _read_schema_version(conn)
    if stored is None:
        conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES (?, ?)",
            (SCHEMA_VERSION_KEY, str(SCHEMA_VERSION)),
        )
    from praetor.alerts.outbox import init_health_alert_outbox_schema
    from praetor.tickets.outbox import init_stamp_outbox_schema

    init_stamp_outbox_schema(conn)
    init_health_alert_outbox_schema(conn)
    return StateStore(conn=conn, db_path=db_path)


def read_feed_sequence_next(conn: sqlite3.Connection) -> int:
    """Return the next sequence number that would be assigned (diagnostic/tests)."""
    row = conn.execute(
        "SELECT next_sequence FROM revocation_feed_sequence WHERE id = 1"
    ).fetchone()
    if row is None:
        msg = "revocation_feed_sequence not initialized"
        raise RuntimeError(msg)
    return int(row[0])


def fetch_feed_outbox_row(
    conn: sqlite3.Connection, sequence_number: int
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT sequence_number, revocation_id, directive_id, status, created_at
        FROM revocation_feed_outbox
        WHERE sequence_number = ?
        """,
        (sequence_number,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def fetch_revocation_record_json(
    conn: sqlite3.Connection, revocation_id: str
) -> str | None:
    row = conn.execute(
        "SELECT record_json FROM directive_revocation_records WHERE revocation_id = ?",
        (revocation_id,),
    ).fetchone()
    if row is None:
        return None
    return str(row["record_json"])
