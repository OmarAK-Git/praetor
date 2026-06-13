"""SQLite persistence for analyst annotations linked to decision edicts."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError

from praetor.auth.verifier import (
    TokenVerifier,
    authenticate_annotation_submission,
    verified_record_identity,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.governance import AnalystAnnotation
from praetor.hashing.canonical import canonical_serialize
from praetor.ledger.hash_chain import DECISION_EDICT_RECORD_TYPE
from praetor.state.sqlite_guard import require_critical_transaction

_ANNOTATION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS analyst_annotations (
    annotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    annotation_json TEXT NOT NULL,
    stored_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyst_annotations_decision_id
    ON analyst_annotations(decision_id);
"""


class AnnotationStoreError(Exception):
    """Raised when annotation storage preconditions fail."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class StoredAnnotation:
    annotation_id: int
    decision_id: str
    annotation: AnalystAnnotation
    stored_at: datetime


def init_annotation_schema(conn: sqlite3.Connection) -> None:
    """Create analyst annotation table if missing (additive upgrade)."""
    conn.executescript(_ANNOTATION_SCHEMA_SQL)


def decision_id_exists(conn: sqlite3.Connection, decision_id: str) -> bool:
    """Return whether a completed decision or ledger edict exists for decision_id."""
    row = conn.execute(
        """
        SELECT 1
        FROM completed_decisions
        WHERE decision_id = ?
        LIMIT 1
        """,
        (decision_id,),
    ).fetchone()
    if row is not None:
        return True
    row = conn.execute(
        """
        SELECT 1
        FROM ledger_chain
        WHERE record_type = ?
          AND json_extract(record_json, '$.decision_id') = ?
        LIMIT 1
        """,
        (DECISION_EDICT_RECORD_TYPE, decision_id),
    ).fetchone()
    return row is not None


def fetch_edict_ledger_hash(
    conn: sqlite3.Connection,
    decision_id: str,
) -> str | None:
    """Return the ledger_current_hash for a decision edict, if present."""
    row = conn.execute(
        """
        SELECT ledger_current_hash
        FROM ledger_chain
        WHERE record_type = ?
          AND json_extract(record_json, '$.decision_id') = ?
        LIMIT 1
        """,
        (DECISION_EDICT_RECORD_TYPE, decision_id),
    ).fetchone()
    if row is None:
        return None
    return str(row["ledger_current_hash"])


def _row_to_stored(row: sqlite3.Row) -> StoredAnnotation:
    stored_at = datetime.fromisoformat(str(row["stored_at"]))
    if stored_at.tzinfo is None:
        stored_at = stored_at.replace(tzinfo=UTC)
    return StoredAnnotation(
        annotation_id=int(row["annotation_id"]),
        decision_id=str(row["decision_id"]),
        annotation=AnalystAnnotation.model_validate_json(str(row["annotation_json"])),
        stored_at=stored_at,
    )


def fetch_annotations_for_decision(
    conn: sqlite3.Connection,
    decision_id: str,
) -> list[StoredAnnotation]:
    """Return all stored annotations for a decision, oldest first."""
    rows = conn.execute(
        """
        SELECT annotation_id, decision_id, annotation_json, stored_at
        FROM analyst_annotations
        WHERE decision_id = ?
        ORDER BY annotation_id ASC
        """,
        (decision_id,),
    ).fetchall()
    return [_row_to_stored(row) for row in rows]


def submit_annotation(
    conn: sqlite3.Connection,
    *,
    token: str | None,
    verifier: TokenVerifier,
    decision_id: str,
    disposition_correct: bool,
    corrected_disposition: Disposition | None,
    comment: str,
    timestamp: datetime,
    caller_supplied_reviewer_identity: str | None = None,
) -> StoredAnnotation:
    """Authenticate, validate, and persist an annotation for an existing decision."""
    require_critical_transaction(conn)

    principal = authenticate_annotation_submission(token, verifier)
    reviewer_identity = verified_record_identity(
        principal,
        caller_supplied_identity=caller_supplied_reviewer_identity,
    )

    if not decision_id_exists(conn, decision_id):
        raise AnnotationStoreError(
            "unknown_decision_id",
            f"no decision exists for decision_id {decision_id!r}",
        )

    try:
        annotation = AnalystAnnotation(
            disposition_correct=disposition_correct,
            corrected_disposition=corrected_disposition,
            comment=comment,
            reviewer_identity=reviewer_identity,
            timestamp=timestamp,
        )
    except ValidationError as exc:
        raise AnnotationStoreError(
            "invalid_annotation",
            str(exc),
        ) from exc

    stored_at = datetime.now(UTC)
    annotation_json = canonical_serialize(
        annotation.model_dump(mode="python")
    ).decode("utf-8")

    cursor = conn.execute(
        """
        INSERT INTO analyst_annotations (decision_id, annotation_json, stored_at)
        VALUES (?, ?, ?)
        """,
        (decision_id, annotation_json, stored_at.isoformat()),
    )
    annotation_id_raw = cursor.lastrowid
    if annotation_id_raw is None:
        msg = "annotation insert did not return annotation_id"
        raise RuntimeError(msg)

    return StoredAnnotation(
        annotation_id=int(annotation_id_raw),
        decision_id=decision_id,
        annotation=annotation,
        stored_at=stored_at,
    )
