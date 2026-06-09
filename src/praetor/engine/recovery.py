"""Startup recovery for attempts, ledger gaps, and outstanding directives."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from praetor.config.health_emit import (
    drain_unflushed_health_alerts,
    enqueue_health_alerts_in_transaction,
    flush_health_alert_batch,
    new_health_alert_batch_id,
)
from praetor.config.live import (
    directive_matches_entry,
    permanent_never_contain_entries,
    reconciliation_never_contain_entries,
)
from praetor.config.state import (
    fetch_active_emergency_records,
    fetch_active_snapshot,
    fetch_outstanding_unrevoked_directives,
    mark_directive_revoked,
    read_live_never_contain_entries,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.engine.edict import (
    SkeletonDisposition,
    _finalize_attempt_with_edict_in_transaction,
    build_decision_edict,
    persist_edict_and_complete_attempt,
    skeleton_policy_result,
)
from praetor.engine.ids import decision_id_for_attempt, stamp_evidence_hash
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.hashing import derive_stamp_id
from praetor.ledger.store import append_ledger_record, fetch_ledger_rows
from praetor.policy.state import reconcile_policy_state
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
from praetor.tickets.outbox import StampOutboxEntry, StampStatus, fetch_stamp_outbox
from praetor.tickets.stamp import StampContext, TicketStampBackend, execute_stamp

NEVER_CONTAIN_CONFLICT_ALERT = "never_contain_conflict"


@dataclass(frozen=True)
class StartupRecoveryResult:
    revoked_directive_ids: list[str]
    emitted_health_alert_ids: list[str]


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
    raw = entry_payload.get("candidate_judgment")
    if isinstance(raw, dict):
        return ModelJudgment.model_validate(raw)
    return skeleton_model_judgment()


def _recovery_disposition_for_stamp(
    stamp_status: StampStatus,
    judgment: ModelJudgment,
) -> SkeletonDisposition:
    """Map terminal stamp outcomes per docs/spec.md recovery rules."""
    if stamp_status == StampStatus.FAILED:
        proposed = judgment.proposed_disposition
        final = proposed
        if proposed == Disposition.AUTO_CONTAIN:
            final = Disposition.ESCALATE
        return SkeletonDisposition(
            final_disposition=final,
            fault_flags=["ticket_stamp_failed"],
            system_fault_escalation=False,
            proposed_disposition=proposed,
        )
    disposition = skeleton_policy_result(judgment)
    if disposition.final_disposition == Disposition.AUTO_CONTAIN:
        return SkeletonDisposition(
            final_disposition=Disposition.ESCALATE,
            fault_flags=[],
            system_fault_escalation=False,
            proposed_disposition=judgment.proposed_disposition,
        )
    return disposition


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
    revoked: list[str] = []
    with critical_transaction(conn):
        for directive in fetch_outstanding_unrevoked_directives(conn):
            if not any(directive_matches_entry(directive, e) for e in never_contain):
                continue
            now = datetime.now(UTC)
            record = DirectiveRevocationRecord(
                revocation_id=f"rev-{uuid.uuid4().hex}",
                directive_id=directive.directive_id,
                reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
                reason_code=RevocationReason.NEVER_CONTAIN_CONFLICT.value,
                triggered_by=triggered_by,
                revoked_at=now,
                ledger_commit_at=now,
                idempotency_key_cleared=False,
            )
            store.write_automated_revocation_in_transaction(record)
            append_ledger_record(conn, record)
            mark_directive_revoked(conn, directive.directive_id)
            revoked.append(directive.directive_id)
        if revoked:
            alerts = [
                SystemHealthAlert(
                    alert_code=NEVER_CONTAIN_CONFLICT_ALERT,
                    emitted_at=datetime.now(UTC),
                )
                for _ in revoked
            ]
            enqueue_health_alerts_in_transaction(conn, alerts, batch_id=batch_id)
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
    store.conn.commit()
    revoked, emitted = reconcile_outstanding_directives_never_contain(store)
    return StartupRecoveryResult(
        revoked_directive_ids=revoked,
        emitted_health_alert_ids=emitted,
    )
