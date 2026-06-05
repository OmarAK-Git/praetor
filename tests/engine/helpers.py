"""Shared assertions for TASK-012 engine tests."""

from __future__ import annotations

import sqlite3

from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.policy import PolicyGateResult
from praetor.ledger.hash_chain import verify_edict_has_matching_never_contain_snapshot
from praetor.ledger.store import fetch_ledger_rows

UNDOCUMENTED_FAULT_FLAGS = frozenset(
    {
        "ticket_stamp_unknown",
        "walking_skeleton_no_autocontain",
        "recovery_blocked_autocontain",
    }
)


def assert_outcome_matrix_edict(
    edict: DecisionEdict,
    *,
    final_disposition: Disposition,
    fault_flags: list[str],
    system_fault_escalation: bool,
    proposed_disposition: Disposition | None = None,
) -> None:
    assert edict.final_disposition == final_disposition
    assert edict.fault_flags == fault_flags
    assert edict.system_fault_escalation is system_fault_escalation
    if proposed_disposition is not None:
        assert edict.policy_gate_result == PolicyGateResult(
            proposed_disposition=proposed_disposition,
            final_disposition=final_disposition,
        )
    for flag in edict.fault_flags:
        assert flag not in UNDOCUMENTED_FAULT_FLAGS, f"undocumented fault flag: {flag!r}"


def assert_edict_snapshot_pairing(conn: sqlite3.Connection, edict: DecisionEdict) -> None:
    verify_edict_has_matching_never_contain_snapshot(conn, edict)


def count_ledger_records(conn: sqlite3.Connection, record_type: str) -> int:
    return sum(1 for r in fetch_ledger_rows(conn) if r.record_type == record_type)


def fetch_ledger_edicts(conn: sqlite3.Connection) -> list[DecisionEdict]:
    return [
        DecisionEdict.model_validate_json(r.record_json)
        for r in fetch_ledger_rows(conn)
        if r.record_type == "decision_edict"
    ]


def count_stamp_outbox_rows(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM ticket_stamp_outbox").fetchone()
    assert row is not None
    return int(row["c"])
