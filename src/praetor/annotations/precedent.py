"""Human-confirmed precedent cases for similar-case retrieval."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError

from praetor.contracts.edict import DecisionEdict
from praetor.ledger.hash_chain import DECISION_EDICT_RECORD_TYPE


@dataclass(frozen=True)
class HumanConfirmedPrecedent:
    """A past decision with at least one human-confirmed analyst annotation."""

    annotation_id: int
    decision_id: str
    alert_reference: str
    final_disposition: str
    summary: str
    confirmed_at: datetime


def fetch_human_confirmed_precedents(
    conn: sqlite3.Connection,
) -> list[HumanConfirmedPrecedent]:
    """Return human-confirmed precedents, newest confirmation first."""
    rows = conn.execute(
        """
        SELECT a.annotation_id, a.decision_id, a.annotation_json, a.stored_at
        FROM analyst_annotations a
        INNER JOIN (
            SELECT decision_id, MAX(annotation_id) AS max_annotation_id
            FROM analyst_annotations
            WHERE json_extract(annotation_json, '$.disposition_correct') IN (1, 'true')
            GROUP BY decision_id
        ) confirmed ON a.annotation_id = confirmed.max_annotation_id
        ORDER BY a.stored_at DESC, a.decision_id ASC
        """
    ).fetchall()

    precedents: list[HumanConfirmedPrecedent] = []
    for row in rows:
        edict = _fetch_decision_edict(conn, str(row["decision_id"]))
        if edict is None:
            continue
        annotation_json = str(row["annotation_json"])
        comment = _extract_comment(annotation_json)
        summary = _build_precedent_summary(edict, comment)
        confirmed_at = datetime.fromisoformat(str(row["stored_at"]))
        if confirmed_at.tzinfo is None:
            confirmed_at = confirmed_at.replace(tzinfo=UTC)
        precedents.append(
            HumanConfirmedPrecedent(
                annotation_id=int(row["annotation_id"]),
                decision_id=str(row["decision_id"]),
                alert_reference=edict.alert_reference,
                final_disposition=edict.final_disposition.value,
                summary=summary,
                confirmed_at=confirmed_at,
            )
        )
    return precedents


def _fetch_decision_edict(
    conn: sqlite3.Connection,
    decision_id: str,
) -> DecisionEdict | None:
    row = conn.execute(
        """
        SELECT record_json
        FROM ledger_chain
        WHERE record_type = ?
          AND json_extract(record_json, '$.decision_id') = ?
        LIMIT 1
        """,
        (DECISION_EDICT_RECORD_TYPE, decision_id),
    ).fetchone()
    if row is None:
        return None
    try:
        return DecisionEdict.model_validate_json(str(row["record_json"]))
    except ValidationError:
        return None


def _extract_comment(annotation_json: str) -> str:
    import json

    payload = json.loads(annotation_json)
    return str(payload.get("comment", ""))


def _build_precedent_summary(edict: DecisionEdict, analyst_comment: str) -> str:
    judgment = edict.model_judgment
    parts = [
        judgment.narrative,
        " ".join(judgment.key_tells),
        " ".join(judgment.benign_alternatives),
    ]
    if analyst_comment:
        parts.append(f"Analyst note: {analyst_comment}")
    return " ".join(part.strip() for part in parts if part.strip())
