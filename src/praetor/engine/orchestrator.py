"""Walking skeleton alert intake orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from praetor.config.constants import HARD_CONFIG_CHARACTER_BUDGET
from praetor.config.snapshot import verbatim_character_count
from praetor.config.state import (
    fetch_active_snapshot,
    fetch_verbatim_render_text,
    read_live_never_contain_entries,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.citations import validate_skeleton_citations
from praetor.engine.edict import (
    SkeletonDisposition,
    append_edict_and_snapshot,
    build_decision_edict,
    escalate_disposition,
    persist_edict_and_complete_attempt,
    skeleton_policy_result,
)
from praetor.engine.skeleton import (
    SKELETON_ALERT_ID,
    SKELETON_BUNDLE_HASH,
    SKELETON_EVIDENCE_CATALOG,
    skeleton_model_judgment,
)
from praetor.judgment.prompt import build_judgment_prompt_payload
from praetor.judgment.provider import (
    JudgmentProvider,
    JudgmentRequest,
    ProviderMalformedResponseError,
    ProviderProbeResult,
    ProviderRefusalError,
    ProviderRetryPolicy,
    ProviderTimeoutError,
    call_provider_with_retries,
)
from praetor.state.attempts import (
    AttemptState,
    ProcessingAttempt,
    abort_attempt,
    transition_attempt,
)
from praetor.state.store import StateStore
from praetor.tickets.stamp import (
    StampBackendOutcome,
    StampBackendResult,
    StampContext,
    TicketStampBackend,
    execute_stamp,
)


class CorrelationFailure(Exception):
    """Walking skeleton: bundle could not be assembled."""


@dataclass
class _CountingJudgmentProvider:
    judgment: ModelJudgment
    calls: int = 0

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        _ = request
        self.calls += 1
        return self.judgment

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        _ = canary_payload
        return ProviderProbeResult(
            success=True,
            provider_name="counting",
            model_name="skeleton",
            metadata={},
        )


@dataclass(frozen=True)
class IntakeResult:
    decision_id: str | None
    edict: DecisionEdict | None
    disposition: Disposition | None
    fault_flags: tuple[str, ...]
    attempt_aborted: bool
    judgment_provider_calls: int


@dataclass
class WalkingSkeletonEngine:
    store: StateStore
    judgment_provider: JudgmentProvider
    stamp_backend: TicketStampBackend

    def process_intake(
        self,
        *,
        alert_identity: str = SKELETON_ALERT_ID,
        org_config_snapshot_hash: str | None = None,
        correlate: bool = True,
        enforce_config_budget: bool = True,
        provider_retry_policy: ProviderRetryPolicy | None = None,
    ) -> IntakeResult:
        return process_alert_intake(
            self.store,
            judgment_provider=self.judgment_provider,
            stamp_backend=self.stamp_backend,
            alert_identity=alert_identity,
            org_config_snapshot_hash=org_config_snapshot_hash,
            correlate=correlate,
            enforce_config_budget=enforce_config_budget,
            provider_retry_policy=provider_retry_policy,
        )


def process_alert_intake(
    store: StateStore,
    *,
    judgment_provider: JudgmentProvider,
    stamp_backend: TicketStampBackend,
    alert_identity: str = SKELETON_ALERT_ID,
    org_config_snapshot_hash: str | None = None,
    correlate: bool = True,
    enforce_config_budget: bool = True,
    provider_retry_policy: ProviderRetryPolicy | None = None,
) -> IntakeResult:
    """Run one walking-skeleton intake; caller must have completed startup recovery."""
    snapshot = fetch_active_snapshot(store.conn)
    if snapshot is None:
        msg = "active org config required for intake"
        raise RuntimeError(msg)
    snap_hash = org_config_snapshot_hash or snapshot.snapshot_hash
    bundle_hash = SKELETON_BUNDLE_HASH

    alloc = store.allocate_attempt(
        alert_identity=alert_identity,
        evidence_bundle_hash=bundle_hash,
        org_config_snapshot_hash=snap_hash,
    )
    if alloc.completed is not None:
        return IntakeResult(
            decision_id=alloc.completed.decision_id,
            edict=None,
            disposition=None,
            fault_flags=(),
            attempt_aborted=False,
            judgment_provider_calls=0,
        )
    assert alloc.attempt is not None
    attempt = transition_attempt(
        store.conn, alloc.attempt.processing_attempt_identity, AttemptState.ACTIVE
    )

    if not correlate:
        return _finish_correlation_failure(store, attempt)

    verbatim = fetch_verbatim_render_text(store.conn, snap_hash)
    if enforce_config_budget:
        if (
            verbatim is not None
            and verbatim_character_count(verbatim) > HARD_CONFIG_CHARACTER_BUDGET
        ):
            return _finish_config_over_budget(store, attempt, judgment_provider)

    prompt_payload = build_judgment_prompt_payload(
        evidence_facts=SKELETON_EVIDENCE_CATALOG.values(),
        evidence_bundle_hash=bundle_hash,
        org_config_snapshot_hash=snap_hash,
        org_config_verbatim=verbatim or "",
    )
    request = JudgmentRequest(
        scenario_id=alert_identity,
        payload=prompt_payload,
    )
    try:
        judgment = call_provider_with_retries(
            judgment_provider,
            request,
            retry_policy=provider_retry_policy,
        )
    except ProviderMalformedResponseError:
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag="provider_malformed_json",
        )
    except ProviderTimeoutError:
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag="provider_timeout",
        )
    except ProviderRefusalError:
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag="provider_refusal",
        )
    calls = getattr(judgment_provider, "calls", 0)

    if not validate_skeleton_citations(judgment, SKELETON_EVIDENCE_CATALOG):
        return _finish_invalid_citation(store, attempt, judgment, calls)

    disposition = skeleton_policy_result(judgment)
    if disposition.final_disposition == Disposition.AUTO_CONTAIN:
        disposition = SkeletonDisposition(
            final_disposition=Disposition.ESCALATE,
            fault_flags=[],
            system_fault_escalation=False,
            proposed_disposition=judgment.proposed_disposition,
        )

    transition_attempt(
        store.conn, attempt.processing_attempt_identity, AttemptState.PENDING_STAMP
    )
    stamp_result = execute_stamp(
        store.conn,
        stamp_backend,
        StampContext(
            alert_identity=attempt.alert_identity,
            evidence_bundle_hash=attempt.evidence_bundle_hash,
            org_config_snapshot_hash=attempt.org_config_snapshot_hash,
            processing_attempt_identity=attempt.processing_attempt_identity,
            ticket_payload={
                "candidate_judgment": judgment.model_dump(mode="json"),
            },
        ),
    )
    attempt = transition_attempt(
        store.conn, attempt.processing_attempt_identity, AttemptState.STAMP_RESOLVED
    )
    never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain,
        stamp_status=stamp_result.status.value,
        ticket_stamp_payload=stamp_result.ticket_payload,
    )
    stored = persist_edict_and_complete_attempt(
        store.conn,
        attempt,
        edict,
        never_contain_entries=never_contain,
    )
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=stored.final_disposition,
        fault_flags=tuple(stored.fault_flags),
        attempt_aborted=False,
        judgment_provider_calls=calls,
    )


def _finish_correlation_failure(
    store: StateStore, attempt: ProcessingAttempt
) -> IntakeResult:
    judgment = skeleton_model_judgment(proposed=Disposition.ESCALATE)
    disposition = escalate_disposition(
        proposed=Disposition.ESCALATE,
        fault_flag="correlation_failure",
        system_fault=True,
    )
    never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain,
        stamp_status="not_required",
        ticket_stamp_payload={},
        correlation_failure=True,
    )
    stored = append_edict_and_snapshot(
        store.conn,
        edict=edict,
        never_contain_entries=never_contain,
    )
    abort_attempt(store.conn, attempt.processing_attempt_identity)
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=("correlation_failure",),
        attempt_aborted=True,
        judgment_provider_calls=0,
    )


def _finish_config_over_budget(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment_provider: JudgmentProvider,
) -> IntakeResult:
    judgment = skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)
    disposition = escalate_disposition(
        proposed=Disposition.STANDARD_REVIEW,
        fault_flag="config_over_budget",
        system_fault=True,
    )
    never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain,
        stamp_status="not_required",
        ticket_stamp_payload={},
    )
    stored = persist_edict_and_complete_attempt(
        store.conn,
        attempt,
        edict,
        never_contain_entries=never_contain,
    )
    calls = getattr(judgment_provider, "calls", 0)
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=("config_over_budget",),
        attempt_aborted=False,
        judgment_provider_calls=calls,
    )


def _finish_provider_fault(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment_provider: JudgmentProvider,
    *,
    fault_flag: str,
) -> IntakeResult:
    judgment = skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)
    disposition = escalate_disposition(
        proposed=Disposition.STANDARD_REVIEW,
        fault_flag=fault_flag,
        system_fault=True,
    )
    never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain,
        stamp_status="not_required",
        ticket_stamp_payload={},
    )
    stored = persist_edict_and_complete_attempt(
        store.conn,
        attempt,
        edict,
        never_contain_entries=never_contain,
    )
    calls = getattr(judgment_provider, "calls", 0)
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=(fault_flag,),
        attempt_aborted=False,
        judgment_provider_calls=calls,
    )


def _finish_invalid_citation(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment: ModelJudgment,
    calls: int,
) -> IntakeResult:
    disposition = escalate_disposition(
        proposed=judgment.proposed_disposition,
        fault_flag="invalid_model_citation",
        system_fault=True,
    )
    never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain,
        stamp_status="not_required",
        ticket_stamp_payload={},
    )
    stored = persist_edict_and_complete_attempt(
        store.conn,
        attempt,
        edict,
        never_contain_entries=never_contain,
    )
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=("invalid_model_citation",),
        attempt_aborted=False,
        judgment_provider_calls=calls,
    )


class SucceedingStampBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        _ = stamp_id, payload
        return StampBackendResult(
            outcome=StampBackendOutcome.SUCCEEDED,
            payload={"ticket": "stamped"},
        )
