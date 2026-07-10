"""Append-only SQLite persistence for PolicyGate evaluation dimensions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from praetor.contracts.disposition import Disposition
from praetor.state.sqlite_guard import require_critical_transaction

_EVALUATION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS policy_gate_evaluations (
    evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    proposed_disposition TEXT NOT NULL,
    final_disposition TEXT NOT NULL,
    overridden INTEGER NOT NULL,
    evaluated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policy_gate_evaluations_evaluated_at
    ON policy_gate_evaluations(evaluated_at);

CREATE INDEX IF NOT EXISTS idx_policy_gate_evaluations_decision_id
    ON policy_gate_evaluations(decision_id);
"""


@dataclass(frozen=True)
class PolicyGateEvaluationRow:
    evaluation_id: int
    decision_id: str
    target_type: str
    asset_class: str
    proposed_disposition: str
    final_disposition: str
    overridden: bool
    evaluated_at: datetime


def init_policy_gate_evaluation_schema(conn: sqlite3.Connection) -> None:
    """Create policy_gate_evaluations table if missing (additive upgrade)."""
    conn.executescript(_EVALUATION_SCHEMA_SQL)


def _disposition_key(disposition: Disposition | str) -> str:
    return disposition.value if isinstance(disposition, Disposition) else disposition


def record_policy_gate_evaluation(
    conn: sqlite3.Connection,
    *,
    decision_id: str,
    target_type: str,
    asset_class: str,
    proposed: Disposition | str,
    final: Disposition | str,
    evaluated_at: datetime,
) -> PolicyGateEvaluationRow:
    """Persist one PolicyGate evaluation row for dimensional reporting."""
    require_critical_transaction(conn)

    proposed_key = _disposition_key(proposed)
    final_key = _disposition_key(final)
    overridden = proposed_key != final_key
    if evaluated_at.tzinfo is None:
        evaluated_at = evaluated_at.replace(tzinfo=UTC)

    cursor = conn.execute(
        """
        INSERT INTO policy_gate_evaluations (
            decision_id,
            target_type,
            asset_class,
            proposed_disposition,
            final_disposition,
            overridden,
            evaluated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            target_type,
            asset_class,
            proposed_key,
            final_key,
            int(overridden),
            evaluated_at.isoformat(),
        ),
    )
    evaluation_id_raw = cursor.lastrowid
    if evaluation_id_raw is None:
        msg = "policy_gate_evaluations insert did not return evaluation_id"
        raise RuntimeError(msg)

    return PolicyGateEvaluationRow(
        evaluation_id=int(evaluation_id_raw),
        decision_id=decision_id,
        target_type=target_type,
        asset_class=asset_class,
        proposed_disposition=proposed_key,
        final_disposition=final_key,
        overridden=overridden,
        evaluated_at=evaluated_at,
    )
