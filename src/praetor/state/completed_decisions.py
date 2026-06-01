"""Completed-edict three-tuple storage (docs/contracts.md §6)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class CompletedDecision:
    """Durable completed edict keyed by alert/bundle/config three-tuple."""

    alert_identity: str
    evidence_bundle_hash: str
    org_config_snapshot_hash: str
    decision_id: str
    processing_attempt_identity: str
    completed_at: datetime


def _row_to_completed(row: sqlite3.Row) -> CompletedDecision:
    completed_at = datetime.fromisoformat(str(row["completed_at"]))
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)
    return CompletedDecision(
        alert_identity=str(row["alert_identity"]),
        evidence_bundle_hash=str(row["evidence_bundle_hash"]),
        org_config_snapshot_hash=str(row["org_config_snapshot_hash"]),
        decision_id=str(row["decision_id"]),
        processing_attempt_identity=str(row["processing_attempt_identity"]),
        completed_at=completed_at,
    )


def fetch_completed_decision(
    conn: sqlite3.Connection,
    *,
    alert_identity: str,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
) -> CompletedDecision | None:
    row = conn.execute(
        """
        SELECT alert_identity, evidence_bundle_hash, org_config_snapshot_hash,
               decision_id, processing_attempt_identity, completed_at
        FROM completed_decisions
        WHERE alert_identity = ?
          AND evidence_bundle_hash = ?
          AND org_config_snapshot_hash = ?
        """,
        (alert_identity, evidence_bundle_hash, org_config_snapshot_hash),
    ).fetchone()
    if row is None:
        return None
    return _row_to_completed(row)


def insert_completed_decision(
    conn: sqlite3.Connection,
    *,
    alert_identity: str,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    decision_id: str,
    processing_attempt_identity: str,
) -> CompletedDecision:
    completed_at = datetime.now(UTC)
    try:
        conn.execute(
            """
            INSERT INTO completed_decisions (
                alert_identity, evidence_bundle_hash, org_config_snapshot_hash,
                decision_id, processing_attempt_identity, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alert_identity,
                evidence_bundle_hash,
                org_config_snapshot_hash,
                decision_id,
                processing_attempt_identity,
                completed_at.isoformat(),
            ),
        )
    except sqlite3.IntegrityError as err:
        msg = "completed edict already exists for three-tuple"
        raise CompletedEdictConflictError(msg) from err
    return CompletedDecision(
        alert_identity=alert_identity,
        evidence_bundle_hash=evidence_bundle_hash,
        org_config_snapshot_hash=org_config_snapshot_hash,
        decision_id=decision_id,
        processing_attempt_identity=processing_attempt_identity,
        completed_at=completed_at,
    )


class CompletedEdictConflictError(Exception):
    """Raised when inserting a duplicate completed-edict three-tuple."""
