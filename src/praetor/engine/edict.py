"""Build and persist DecisionEdict records for the walking skeleton."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.fault_flags import validate_decision_edict_fault_flags
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.ledger import NeverContainSnapshotRecord
from praetor.contracts.policy import PolicyGateResult
from praetor.engine.ids import resolved_evidence_bundle_hash
from praetor.hashing import compute_never_contain_entries_hash, derive_decision_id
from praetor.ledger.store import append_ledger_record
from praetor.state.attempts import (
    AttemptState,
    InvalidTransitionError,
    ProcessingAttempt,
)
from praetor.state.completed_decisions import insert_completed_decision
from praetor.state.sqlite_guard import (
    critical_transaction,
    require_critical_transaction,
)


@dataclass(frozen=True)
class SkeletonDisposition:
    final_disposition: Disposition
    fault_flags: list[str]
    system_fault_escalation: bool
    proposed_disposition: Disposition


def skeleton_policy_result(judgment: ModelJudgment) -> SkeletonDisposition:
    """Minimal policy: never auto_contain; pass through propose for non-escalate paths."""
    proposed = judgment.proposed_disposition
    if proposed == Disposition.AUTO_CONTAIN:
        return SkeletonDisposition(
            final_disposition=Disposition.ESCALATE,
            fault_flags=[],
            system_fault_escalation=False,
            proposed_disposition=proposed,
        )
    return SkeletonDisposition(
        final_disposition=proposed,
        fault_flags=[],
        system_fault_escalation=False,
        proposed_disposition=proposed,
    )


def escalate_disposition(
    *,
    proposed: Disposition,
    fault_flag: str,
    system_fault: bool,
) -> SkeletonDisposition:
    return SkeletonDisposition(
        final_disposition=Disposition.ESCALATE,
        fault_flags=[fault_flag],
        system_fault_escalation=system_fault,
        proposed_disposition=proposed,
    )


def build_decision_edict(
    *,
    attempt: ProcessingAttempt,
    judgment: ModelJudgment,
    disposition: SkeletonDisposition,
    live_never_contain_entries: list[dict[str, Any]],
    stamp_status: str,
    ticket_stamp_payload: dict[str, Any],
    correlation_failure: bool = False,
    ledger_previous_hash: str | None = None,
    ledger_current_hash: str = "pending",
) -> DecisionEdict:
    validate_decision_edict_fault_flags(
        fault_flags=disposition.fault_flags,
        system_fault_escalation=disposition.system_fault_escalation,
        final_disposition=disposition.final_disposition,
    )
    # Single EMPTY_BUNDLE substitution: this resolved value feeds both the
    # decision_id derivation and the stored evidence_bundle_hash field (§3.3).
    bundle_hash = resolved_evidence_bundle_hash(
        attempt.evidence_bundle_hash,
        correlation_failure=correlation_failure,
    )
    decision_id = derive_decision_id(
        attempt.alert_identity,
        bundle_hash,
        attempt.org_config_snapshot_hash,
        attempt.processing_attempt_identity,
    )
    live_hash = compute_never_contain_entries_hash(live_never_contain_entries)
    return DecisionEdict(
        decision_id=decision_id,
        alert_reference=attempt.alert_identity,
        evidence_bundle_hash=bundle_hash,
        org_config_snapshot_hash=attempt.org_config_snapshot_hash,
        live_never_contain_hash=live_hash,
        model_judgment=judgment,
        policy_gate_result=PolicyGateResult(
            proposed_disposition=disposition.proposed_disposition,
            final_disposition=disposition.final_disposition,
        ),
        final_disposition=disposition.final_disposition,
        system_fault_escalation=disposition.system_fault_escalation,
        fault_flags=disposition.fault_flags,
        stamp_status=stamp_status,
        timing_metadata={"decided_at_source": "walking_skeleton"},
        ledger_previous_hash=ledger_previous_hash,
        ledger_current_hash=ledger_current_hash,
        ticket_stamp_payload=ticket_stamp_payload,
        decided_at=datetime.now(UTC),
    )


def _append_edict_and_snapshot_in_transaction(
    conn: sqlite3.Connection,
    *,
    edict: DecisionEdict,
    never_contain_entries: list[dict[str, Any]],
) -> DecisionEdict:
    require_critical_transaction(conn)
    snapshot_content = never_contain_entries
    snapshot = NeverContainSnapshotRecord(
        snapshot_id=f"snap-{edict.decision_id[:16]}",
        snapshot_hash=compute_never_contain_entries_hash(snapshot_content),
        snapshot_content=snapshot_content,
        evaluated_at=edict.decided_at,
        triggered_by_decision_id=edict.decision_id,
    )
    append_ledger_record(conn, snapshot)
    result = append_ledger_record(conn, edict)
    return DecisionEdict.model_validate_json(result.record_json)


_NEXT_TOWARD_READY: dict[AttemptState, AttemptState | None] = {
    AttemptState.ALLOCATED: AttemptState.ACTIVE,
    AttemptState.ACTIVE: AttemptState.PENDING_STAMP,
    AttemptState.PENDING_STAMP: AttemptState.STAMP_RESOLVED,
    AttemptState.STAMP_RESOLVED: AttemptState.READY_TO_APPEND,
    AttemptState.READY_TO_APPEND: None,
}


def _advance_attempt_to_ready_in_transaction(
    conn: sqlite3.Connection, attempt: ProcessingAttempt
) -> ProcessingAttempt:
    current = attempt
    while current.state != AttemptState.READY_TO_APPEND:
        nxt = _NEXT_TOWARD_READY.get(current.state)
        if nxt is None:
            msg = f"cannot advance attempt from state {current.state.value!r}"
            raise InvalidTransitionError(msg)
        current = _transition_attempt_in_transaction(
            conn, current.processing_attempt_identity, nxt
        )
    return current


def _finalize_attempt_with_edict_in_transaction(
    conn: sqlite3.Connection,
    attempt: ProcessingAttempt,
    edict: DecisionEdict,
) -> None:
    require_critical_transaction(conn)
    current = _advance_attempt_to_ready_in_transaction(conn, attempt)
    insert_completed_decision(
        conn,
        alert_identity=current.alert_identity,
        evidence_bundle_hash=edict.evidence_bundle_hash,
        org_config_snapshot_hash=edict.org_config_snapshot_hash,
        decision_id=edict.decision_id,
        processing_attempt_identity=current.processing_attempt_identity,
    )
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        UPDATE processing_attempts
        SET state = ?, updated_at = ?
        WHERE attempt_id = ?
        """,
        (
            AttemptState.COMPLETED.value,
            now,
            int(current.processing_attempt_identity),
        ),
    )


def _transition_attempt_in_transaction(
    conn: sqlite3.Connection,
    processing_attempt_identity: str,
    new_state: AttemptState,
) -> ProcessingAttempt:
    """Transition without opening a nested critical_transaction."""
    require_critical_transaction(conn)
    from praetor.state.attempts import (
        _ALLOWED_TRANSITIONS,
        AttemptNotFoundError,
        InvalidTransitionError,
        _fetch_attempt_by_id,
    )

    attempt = _fetch_attempt_by_id(conn, processing_attempt_identity)
    if attempt is None:
        msg = f"attempt not found: {processing_attempt_identity!r}"
        raise AttemptNotFoundError(msg)
    allowed = _ALLOWED_TRANSITIONS.get(attempt.state, frozenset())
    if new_state not in allowed:
        msg = f"invalid transition {attempt.state.value!r} -> {new_state.value!r}"
        raise InvalidTransitionError(msg)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        UPDATE processing_attempts
        SET state = ?, updated_at = ?
        WHERE attempt_id = ?
        """,
        (new_state.value, now, int(processing_attempt_identity)),
    )
    updated = _fetch_attempt_by_id(conn, processing_attempt_identity)
    assert updated is not None
    return updated


def append_edict_and_snapshot(
    conn: sqlite3.Connection,
    *,
    edict: DecisionEdict,
    never_contain_entries: list[dict[str, Any]],
) -> DecisionEdict:
    """Append never-contain snapshot then decision edict inside critical_transaction."""
    with critical_transaction(conn):
        return _append_edict_and_snapshot_in_transaction(
            conn, edict=edict, never_contain_entries=never_contain_entries
        )


def finalize_attempt_with_edict(
    conn: sqlite3.Connection,
    attempt: ProcessingAttempt,
    edict: DecisionEdict,
) -> None:
    """Record completed decision row and mark attempt completed."""
    with critical_transaction(conn):
        _finalize_attempt_with_edict_in_transaction(conn, attempt, edict)


def persist_edict_and_complete_attempt(
    conn: sqlite3.Connection,
    attempt: ProcessingAttempt,
    edict: DecisionEdict,
    *,
    never_contain_entries: list[dict[str, Any]],
    in_transaction_hook: Callable[[sqlite3.Connection], None] | None = None,
) -> DecisionEdict:
    """Append ledger records and complete attempt in one critical transaction."""
    with critical_transaction(conn):
        stored = _append_edict_and_snapshot_in_transaction(
            conn, edict=edict, never_contain_entries=never_contain_entries
        )
        if in_transaction_hook is not None:
            in_transaction_hook(conn)
        _finalize_attempt_with_edict_in_transaction(conn, attempt, stored)
        return stored
