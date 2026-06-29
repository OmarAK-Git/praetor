"""Startup recovery for attempts, ledger gaps, and outstanding directives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from praetor.config.health_emit import (
    drain_unflushed_health_alerts,
    enqueue_health_alerts_in_transaction,
    flush_health_alert_batch,
    new_health_alert_batch_id,
)
from praetor.config.live import (
    permanent_never_contain_entries,
    reconciliation_never_contain_entries,
)
from praetor.config.state import (
    fetch_active_emergency_records,
    fetch_active_snapshot,
    fetch_outstanding_unrevoked_directives,
    read_live_never_contain_entries,
)
from praetor.containment.revocation import (
    never_contain_conflict_alerts,
    orphan_outstanding_directive_alert,
    revoke_directives_matching_never_contain,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.ledger import RevocationReason
from praetor.engine.edict import (
    SkeletonDisposition,
    _finalize_attempt_with_edict_in_transaction,
    build_decision_edict,
    escalate_disposition,
    persist_edict_and_complete_attempt,
    skeleton_policy_result,
)
from praetor.engine.ids import decision_id_for_attempt, stamp_evidence_hash
from praetor.engine.queue_policy import queue_aging_exceeded_for_snapshot
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.hashing import derive_stamp_id
from praetor.ledger.store import fetch_ledger_rows
from praetor.policy.gate import QUEUE_AGING_EXCEEDED
from praetor.policy.state import (
    fetch_orphan_outstanding_directives,
    reconcile_policy_state,
)
from praetor.state.attempts import (
    AttemptState,
    ProcessingAttempt,
    _fetch_attempt_by_id,
    abort_attempt,
    fetch_all_non_terminal_attempts,
    transition_attempt,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore
from praetor.tickets.contract import (
    StampContractDisposition,
    apply_terminal_stamp_to_disposition,
    candidate_judgment_from_stamp_payload,
)
from praetor.tickets.outbox import StampOutboxEntry, StampStatus, fetch_stamp_outbox
from praetor.tickets.stamp import StampContext, TicketStampBackend, execute_stamp


@dataclass(frozen=True)
class StartupRecoveryResult:
    revoked_directive_ids: list[str]
    emitted_health_alert_ids: list[str]
    orphan_directive_alert_ids: list[str]


class _NoOpStampBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> Any:
        from praetor.tickets.stamp import StampBackendOutcome, StampBackendResult

        _ = stamp_id, payload
        return StampBackendResult(outcome=StampBackendOutcome.SUCCEEDED, payload={})


def ledger_has_edict_for_decision_id(
    conn: Any,
    decision_id: str,
) -> bool:
    for row in fetch_ledger_rows(conn):
        if row.record_type != "decision_edict":
            continue
        edict = DecisionEdict.model_validate_json(row.record_json)
        if edict.decision_id == decision_id:
            return True
    return False


def _stamp_id_for_attempt(attempt: ProcessingAttempt) -> str:
    bundle_for_stamp = stamp_evidence_hash(
        evidence_bundle_hash_value=attempt.evidence_bundle_hash
    )
    return derive_stamp_id(
        attempt.alert_identity,
        bundle_for_stamp,
        attempt.org_config_snapshot_hash,
    )


def _recovery_judgment_from_stamp(entry_payload: dict[str, Any]) -> ModelJudgment:
    recovered = candidate_judgment_from_stamp_payload(entry_payload)
    if recovered is not None:
        return recovered
    return skeleton_model_judgment()


def _recovery_disposition_for_stamp(
    stamp_status: StampStatus,
    judgment: ModelJudgment,
) -> SkeletonDisposition:
    """Map terminal stamp outcomes per docs/spec.md recovery rules."""
    pre_stamp = skeleton_policy_result(judgment)
    if pre_stamp.final_disposition == Disposition.AUTO_CONTAIN:
        pre_stamp = SkeletonDisposition(
            final_disposition=Disposition.ESCALATE,
            fault_flags=[],
            system_fault_escalation=False,
            proposed_disposition=judgment.proposed_disposition,
        )
    contract_pre = StampContractDisposition(
        final_disposition=pre_stamp.final_disposition,
        fault_flags=list(pre_stamp.fault_flags),
        system_fault_escalation=pre_stamp.system_fault_escalation,
        proposed_disposition=pre_stamp.proposed_disposition,
    )
    contract_result = apply_terminal_stamp_to_disposition(
        stamp_status,
        pre_stamp_disposition=contract_pre,
    )
    return SkeletonDisposition(
        final_disposition=contract_result.final_disposition,
        fault_flags=list(contract_result.fault_flags),
        system_fault_escalation=contract_result.system_fault_escalation,
        proposed_disposition=contract_result.proposed_disposition,
    )


def _ensure_terminal_stamp(
    conn: Any,
    attempt: ProcessingAttempt,
    backend: TicketStampBackend,
) -> StampOutboxEntry | None:
    """Retry unknown stamps; return terminal outbox row or None to abort."""
    stamp_id = _stamp_id_for_attempt(attempt)
    entry = fetch_stamp_outbox(conn, stamp_id)
    payload = (
        entry.ticket_payload
        if entry is not None
        else {"candidate_judgment": skeleton_model_judgment().model_dump()}
    )
    if entry is None or entry.status in (
        StampStatus.PENDING,
        StampStatus.UNKNOWN,
    ):
        execute_stamp(
            conn,
            backend,
            StampContext(
                alert_identity=attempt.alert_identity,
                evidence_bundle_hash=attempt.evidence_bundle_hash,
                org_config_snapshot_hash=attempt.org_config_snapshot_hash,
                processing_attempt_identity=attempt.processing_attempt_identity,
                ticket_payload=payload,
            ),
        )
        entry = fetch_stamp_outbox(conn, stamp_id)
    if entry is None:
        return None
    if entry.status == StampStatus.UNKNOWN:
        execute_stamp(
            conn,
            backend,
            StampContext(
                alert_identity=attempt.alert_identity,
                evidence_bundle_hash=attempt.evidence_bundle_hash,
                org_config_snapshot_hash=attempt.org_config_snapshot_hash,
                processing_attempt_identity=attempt.processing_attempt_identity,
                ticket_payload=entry.ticket_payload,
            ),
        )
        entry = fetch_stamp_outbox(conn, stamp_id)
    if entry is None or entry.status == StampStatus.UNKNOWN:
        return None
    if entry.status not in (StampStatus.SUCCEEDED, StampStatus.FAILED):
        return None
    return entry


def append_recovery_edict_for_attempt(
    conn: Any,
    attempt: ProcessingAttempt,
    *,
    stamp_status: str,
    ticket_stamp_payload: dict[str, Any],
    judgment: ModelJudgment,
    disposition: SkeletonDisposition,
    never_contain_entries: list[dict[str, Any]],
    correlation_failure: bool = False,
) -> DecisionEdict:
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain_entries,
        stamp_status=stamp_status,
        ticket_stamp_payload=ticket_stamp_payload,
        correlation_failure=correlation_failure,
    )
    return persist_edict_and_complete_attempt(
        conn,
        attempt,
        edict,
        never_contain_entries=never_contain_entries,
    )


def recover_single_attempt(
    store: StateStore,
    attempt: ProcessingAttempt,
    backend: TicketStampBackend,
) -> None:
    """Resolve one non-terminal attempt; never emits auto_contain."""
    conn = store.conn
    never_contain = read_live_never_contain_entries(conn)

    if attempt.state in (AttemptState.ALLOCATED, AttemptState.ACTIVE):
        # Queue aging applies only while the attempt has not entered stamp
        # resolution; recovery is the production detector (DEC-040).
        snapshot = fetch_active_snapshot(conn)
        if snapshot is not None and queue_aging_exceeded_for_snapshot(
            attempt, snapshot
        ):
            judgment = skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)
            disposition = escalate_disposition(
                proposed=Disposition.STANDARD_REVIEW,
                fault_flag=QUEUE_AGING_EXCEEDED,
                system_fault=True,
            )
            append_recovery_edict_for_attempt(
                conn,
                attempt,
                stamp_status="not_required",
                ticket_stamp_payload={},
                judgment=judgment,
                disposition=disposition,
                never_contain_entries=never_contain,
            )
            return
        abort_attempt(conn, attempt.processing_attempt_identity)
        return

    if attempt.state == AttemptState.PENDING_STAMP:
        entry = _ensure_terminal_stamp(conn, attempt, backend)
        if entry is None:
            abort_attempt(conn, attempt.processing_attempt_identity)
            return
        transition_attempt(
            conn, attempt.processing_attempt_identity, AttemptState.STAMP_RESOLVED
        )
        refreshed = _fetch_attempt_by_id(conn, attempt.processing_attempt_identity)
        assert refreshed is not None
        attempt = refreshed

    if attempt.state in (AttemptState.STAMP_RESOLVED, AttemptState.READY_TO_APPEND):
        decision_id = decision_id_for_attempt(
            alert_identity=attempt.alert_identity,
            evidence_bundle_hash_value=attempt.evidence_bundle_hash,
            org_config_snapshot_hash=attempt.org_config_snapshot_hash,
            processing_attempt_identity=attempt.processing_attempt_identity,
        )
        if ledger_has_edict_for_decision_id(conn, decision_id):
            edict_row = next(
                r
                for r in fetch_ledger_rows(conn)
                if r.record_type == "decision_edict"
                and DecisionEdict.model_validate_json(r.record_json).decision_id
                == decision_id
            )
            stored = DecisionEdict.model_validate_json(edict_row.record_json)
            with critical_transaction(conn):
                _finalize_attempt_with_edict_in_transaction(conn, attempt, stored)
            return

        entry = _ensure_terminal_stamp(conn, attempt, backend)
        if entry is None:
            abort_attempt(conn, attempt.processing_attempt_identity)
            return
        judgment = _recovery_judgment_from_stamp(entry.ticket_payload)
        disposition = _recovery_disposition_for_stamp(entry.status, judgment)
        append_recovery_edict_for_attempt(
            conn,
            attempt,
            stamp_status=entry.status.value,
            ticket_stamp_payload=entry.ticket_payload,
            judgment=judgment,
            disposition=disposition,
            never_contain_entries=never_contain,
        )


def surface_orphan_outstanding_directive_alerts(conn: Any) -> list[str]:
    """Emit one durable health alert per orphan directive (idempotent per directive_id)."""
    from praetor.alerts.outbox import (
        fetch_health_alert_outbox,
        write_pending_health_alert,
    )
    from praetor.config.health_emit import init_health_alert_emit_schema

    init_health_alert_emit_schema(conn)
    emitted: list[str] = []
    for directive in fetch_orphan_outstanding_directives(conn):
        alert_id = f"orphan-directive-{directive.directive_id}"
        if fetch_health_alert_outbox(conn, alert_id) is not None:
            continue
        write_pending_health_alert(
            conn,
            orphan_outstanding_directive_alert(),
            alert_id=alert_id,
        )
        emitted.append(alert_id)
    return emitted


def reconcile_outstanding_directives_never_contain(
    store: StateStore,
    *,
    triggered_by: str = "startup_recovery",
) -> tuple[list[str], list[str]]:
    """Revoke matching directives; emit never_contain_conflict health alerts.

    The returned alert-id list contains only the ``never_contain_conflict`` alerts
    emitted by this scan. Pre-existing unflushed alerts from prior partial failures
    are drained as a side effect but excluded from the returned list.
    """
    conn = store.conn
    snapshot = fetch_active_snapshot(conn)
    if snapshot is None:
        return [], []
    perm_entries = permanent_never_contain_entries(
        snapshot.containment_exclusions.model_dump(mode="json")
    )
    emergencies = fetch_active_emergency_records(conn)
    never_contain = reconciliation_never_contain_entries(perm_entries, emergencies)
    batch_id = new_health_alert_batch_id()
    # Recover any prior partial-failure alerts (side effect only; not returned).
    drain_unflushed_health_alerts(conn)
    with critical_transaction(conn):
        directives = fetch_outstanding_unrevoked_directives(conn)
        revoked = revoke_directives_matching_never_contain(
            conn,
            store,
            directives,
            never_contain,
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            triggered_by=triggered_by,
        )
        if revoked:
            enqueue_health_alerts_in_transaction(
                conn,
                never_contain_conflict_alerts(len(revoked)),
                batch_id=batch_id,
            )
    emitted = flush_health_alert_batch(conn, batch_id=batch_id)
    return revoked, emitted


def run_engine_startup_recovery(
    store: StateStore,
    *,
    stamp_backend: TicketStampBackend | None = None,
) -> StartupRecoveryResult:
    """Spec startup steps 4, 5, 6, and 7.

    Implements: enumerate/resolve non-terminal attempts (4), append safe edicts for
    stamp-resolved/ready-to-append attempts missing a ledger edict (5), reconcile
    idempotency keys / rate counters / breaker state (6), and scan outstanding
    directives against current never-contain (7).
    """
    backend = stamp_backend or _NoOpStampBackend()
    for attempt in fetch_all_non_terminal_attempts(store.conn):
        recover_single_attempt(store, attempt, backend)
    reconcile_policy_state(store.conn)
    orphan_alerts = surface_orphan_outstanding_directive_alerts(store.conn)
    store.conn.commit()
    revoked, emitted = reconcile_outstanding_directives_never_contain(store)
    return StartupRecoveryResult(
        revoked_directive_ids=revoked,
        emitted_health_alert_ids=emitted,
        orphan_directive_alert_ids=orphan_alerts,
    )
