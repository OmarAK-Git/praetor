"""SQLite persistence for org config binding, emergencies, and outstanding directives."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from praetor.config.errors import SnapshotHashConflictError, SnapshotTamperError
from praetor.config.live import (
    canonical_target_specification,
    combined_live_never_contain_entries,
    permanent_never_contain_entries,
    target_in_never_contain_list,
)
from praetor.config.snapshot import compute_snapshot_hash, verify_snapshot_hash
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.ledger import EmergencyNeverContainRecord
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.hashing.canonical import sha256_hex


@dataclass(frozen=True)
class ActiveOrgConfig:
    snapshot_hash: str
    verbatim_render_id: str
    activated_at: str


def compute_verbatim_render_id(verbatim_render_text: str) -> str:
    return sha256_hex(verbatim_render_text.encode("utf-8"))


_CONFIG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS org_config_snapshots (
    snapshot_hash TEXT PRIMARY KEY,
    snapshot_json TEXT NOT NULL,
    verbatim_render_text TEXT NOT NULL,
    bound_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS org_config_verbatim_renders (
    snapshot_hash TEXT NOT NULL,
    verbatim_render_id TEXT NOT NULL,
    verbatim_render_text TEXT NOT NULL,
    bound_at TEXT NOT NULL,
    PRIMARY KEY (snapshot_hash, verbatim_render_id),
    FOREIGN KEY (snapshot_hash) REFERENCES org_config_snapshots(snapshot_hash)
);

CREATE TABLE IF NOT EXISTS active_org_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    snapshot_hash TEXT NOT NULL,
    verbatim_render_id TEXT NOT NULL,
    activated_at TEXT NOT NULL,
    FOREIGN KEY (snapshot_hash) REFERENCES org_config_snapshots(snapshot_hash)
);

CREATE TABLE IF NOT EXISTS emergency_never_contain_records (
    entry_id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    added_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outstanding_containment_directives (
    directive_id TEXT PRIMARY KEY,
    directive_json TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS health_alert_pending_flush (
    pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    alert_id TEXT NOT NULL UNIQUE,
    alert_json TEXT NOT NULL,
    flushed INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_outstanding_unrevoked
    ON outstanding_containment_directives(revoked, expires_at);

CREATE INDEX IF NOT EXISTS idx_health_alert_pending_unflushed
    ON health_alert_pending_flush(flushed, batch_id);
"""


def _migrate_config_schema(conn: sqlite3.Connection) -> None:
    active_cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(active_org_config)").fetchall()
    }
    if active_cols and "verbatim_render_id" not in active_cols:
        conn.execute(
            "ALTER TABLE active_org_config ADD COLUMN verbatim_render_id TEXT NOT NULL DEFAULT ''"
        )
    pending_cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(health_alert_pending_flush)").fetchall()
    }
    if pending_cols and "alert_id" not in pending_cols:
        conn.execute(
            "ALTER TABLE health_alert_pending_flush ADD COLUMN alert_id TEXT"
        )


def init_config_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_CONFIG_SCHEMA_SQL)
    _migrate_config_schema(conn)


def _bind_verbatim_render(
    conn: sqlite3.Connection,
    snapshot_hash: str,
    verbatim_render_text: str,
) -> str:
    verbatim_render_id = compute_verbatim_render_id(verbatim_render_text)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO org_config_verbatim_renders (
            snapshot_hash, verbatim_render_id, verbatim_render_text, bound_at
        ) VALUES (?, ?, ?, ?)
        """,
        (snapshot_hash, verbatim_render_id, verbatim_render_text, now),
    )
    return verbatim_render_id


def persist_org_config_snapshot(
    conn: sqlite3.Connection,
    snapshot: OrgConfigSnapshot,
    *,
    verbatim_render_text: str,
) -> str:
    """Persist binding body and verbatim render; returns verbatim_render_id."""
    verify_snapshot_hash(snapshot)
    payload = snapshot.model_dump_json()
    row = conn.execute(
        "SELECT snapshot_json FROM org_config_snapshots WHERE snapshot_hash = ?",
        (snapshot.snapshot_hash,),
    ).fetchone()
    if row is not None:
        existing = OrgConfigSnapshot.model_validate_json(str(row["snapshot_json"]))
        if compute_snapshot_hash(existing) != snapshot.snapshot_hash:
            msg = f"snapshot hash conflict for {snapshot.snapshot_hash!r}"
            raise SnapshotHashConflictError(msg)
        if existing.model_dump_json() != payload:
            msg = f"conflicting binding body for hash {snapshot.snapshot_hash!r}"
            raise SnapshotHashConflictError(msg)
    else:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT INTO org_config_snapshots (
                snapshot_hash, snapshot_json, verbatim_render_text, bound_at
            ) VALUES (?, ?, ?, ?)
            """,
            (snapshot.snapshot_hash, payload, verbatim_render_text, now),
        )
    return _bind_verbatim_render(conn, snapshot.snapshot_hash, verbatim_render_text)


def fetch_snapshot_by_hash(
    conn: sqlite3.Connection,
    snapshot_hash: str,
) -> OrgConfigSnapshot | None:
    row = conn.execute(
        """
        SELECT snapshot_json FROM org_config_snapshots
        WHERE snapshot_hash = ?
        """,
        (snapshot_hash,),
    ).fetchone()
    if row is None:
        return None
    snapshot = OrgConfigSnapshot.model_validate_json(str(row["snapshot_json"]))
    if snapshot.snapshot_hash != snapshot_hash:
        msg = f"stored snapshot_hash field mismatch for {snapshot_hash!r}"
        raise SnapshotTamperError(msg)
    if compute_snapshot_hash(snapshot) != snapshot_hash:
        msg = f"stored snapshot tampered or corrupt: {snapshot_hash!r}"
        raise SnapshotTamperError(msg)
    verify_snapshot_hash(snapshot)
    return snapshot


def fetch_verbatim_render_text(
    conn: sqlite3.Connection,
    snapshot_hash: str,
    *,
    verbatim_render_id: str | None = None,
) -> str | None:
    if verbatim_render_id is None:
        active = fetch_active_org_config(conn)
        if active is not None and active.snapshot_hash == snapshot_hash:
            verbatim_render_id = active.verbatim_render_id
        else:
            row = conn.execute(
                """
                SELECT verbatim_render_text FROM org_config_verbatim_renders
                WHERE snapshot_hash = ?
                ORDER BY bound_at
                LIMIT 1
                """,
                (snapshot_hash,),
            ).fetchone()
            if row is None:
                legacy = conn.execute(
                    """
                    SELECT verbatim_render_text FROM org_config_snapshots
                    WHERE snapshot_hash = ?
                    """,
                    (snapshot_hash,),
                ).fetchone()
                return None if legacy is None else str(legacy["verbatim_render_text"])
            return str(row["verbatim_render_text"])
    row = conn.execute(
        """
        SELECT verbatim_render_text FROM org_config_verbatim_renders
        WHERE snapshot_hash = ? AND verbatim_render_id = ?
        """,
        (snapshot_hash, verbatim_render_id),
    ).fetchone()
    if row is None:
        return None
    return str(row["verbatim_render_text"])


def fetch_active_org_config(conn: sqlite3.Connection) -> ActiveOrgConfig | None:
    row = conn.execute(
        """
        SELECT snapshot_hash, verbatim_render_id, activated_at
        FROM active_org_config WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return None
    return ActiveOrgConfig(
        snapshot_hash=str(row["snapshot_hash"]),
        verbatim_render_id=str(row["verbatim_render_id"]),
        activated_at=str(row["activated_at"]),
    )


def fetch_active_snapshot(conn: sqlite3.Connection) -> OrgConfigSnapshot | None:
    active = fetch_active_org_config(conn)
    if active is None:
        return None
    return fetch_snapshot_by_hash(conn, active.snapshot_hash)


def activate_org_config_record(
    conn: sqlite3.Connection,
    snapshot: OrgConfigSnapshot,
    *,
    verbatim_render_text: str,
) -> ActiveOrgConfig:
    verbatim_render_id = persist_org_config_snapshot(
        conn, snapshot, verbatim_render_text=verbatim_render_text
    )
    now = datetime.now(UTC).isoformat()
    conn.execute("DELETE FROM active_org_config")
    conn.execute(
        """
        INSERT INTO active_org_config (
            id, snapshot_hash, verbatim_render_id, activated_at
        ) VALUES (1, ?, ?, ?)
        """,
        (snapshot.snapshot_hash, verbatim_render_id, now),
    )
    return ActiveOrgConfig(
        snapshot_hash=snapshot.snapshot_hash,
        verbatim_render_id=verbatim_render_id,
        activated_at=now,
    )


def insert_emergency_record(
    conn: sqlite3.Connection,
    record: EmergencyNeverContainRecord,
) -> None:
    conn.execute(
        """
        INSERT INTO emergency_never_contain_records (
            entry_id, record_json, added_at, expires_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            record.entry_id,
            record.model_dump_json(),
            record.added_at.isoformat(),
            record.expires_at.isoformat(),
        ),
    )


def fetch_active_emergency_records(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> list[EmergencyNeverContainRecord]:
    moment = (now or datetime.now(UTC)).isoformat()
    rows = conn.execute(
        """
        SELECT record_json FROM emergency_never_contain_records
        WHERE expires_at > ?
        ORDER BY added_at
        """,
        (moment,),
    ).fetchall()
    return [
        EmergencyNeverContainRecord.model_validate_json(str(row["record_json"]))
        for row in rows
    ]


def retire_emergencies_absorbed_into_permanent(
    conn: sqlite3.Connection,
    permanent_entries: list[dict[str, Any]],
) -> list[str]:
    """Remove active emergencies whose targets are now in permanent never-contain."""
    retired: list[str] = []
    for record in fetch_active_emergency_records(conn):
        spec = canonical_target_specification(record.target_specification)
        if target_in_never_contain_list(
            spec["target_type"], spec["target_id"], permanent_entries
        ):
            conn.execute(
                "DELETE FROM emergency_never_contain_records WHERE entry_id = ?",
                (record.entry_id,),
            )
            retired.append(record.entry_id)
    return retired


def fetch_outstanding_unrevoked_directives(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> list[ContainmentDirective]:
    """Live outstanding directives used for suppression, scans, and step-6 reconcile."""
    moment = (now or datetime.now(UTC)).isoformat()
    rows = conn.execute(
        """
        SELECT directive_json FROM outstanding_containment_directives
        WHERE revoked = 0 AND expires_at > ?
        ORDER BY issued_at
        """,
        (moment,),
    ).fetchall()
    result: list[ContainmentDirective] = []
    for row in rows:
        directive = ContainmentDirective.model_validate_json(str(row["directive_json"]))
        if _directive_has_revocation(conn, directive.directive_id):
            continue
        result.append(directive)
    return result


def fetch_expired_unrevoked_directives(
    conn: sqlite3.Connection,
    *,
    now: datetime | None = None,
) -> list[ContainmentDirective]:
    """Audit-residue rows excluded from outstanding scans (DEC-060 §4.2.1)."""
    moment = (now or datetime.now(UTC)).isoformat()
    rows = conn.execute(
        """
        SELECT directive_json FROM outstanding_containment_directives
        WHERE revoked = 0 AND expires_at <= ?
        ORDER BY issued_at
        """,
        (moment,),
    ).fetchall()
    return [
        ContainmentDirective.model_validate_json(str(row["directive_json"]))
        for row in rows
    ]


def _directive_has_revocation(conn: sqlite3.Connection, directive_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM directive_revocation_records
        WHERE directive_id = ?
        LIMIT 1
        """,
        (directive_id,),
    ).fetchone()
    return row is not None


def mark_directive_revoked(conn: sqlite3.Connection, directive_id: str) -> None:
    conn.execute(
        """
        UPDATE outstanding_containment_directives
        SET revoked = 1
        WHERE directive_id = ?
        """,
        (directive_id,),
    )


def read_live_never_contain_entries(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    snapshot = fetch_active_snapshot(conn)
    permanent: list[dict[str, Any]] = []
    if snapshot is not None:
        permanent = permanent_never_contain_entries(
            snapshot.containment_exclusions.model_dump(mode="json")
        )
    emergencies = fetch_active_emergency_records(conn)
    return combined_live_never_contain_entries(permanent, emergencies)
