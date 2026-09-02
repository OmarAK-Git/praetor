"""Walking skeleton alert intake orchestration."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
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
from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.citations import validate_skeleton_citations
from praetor.engine.edict import (
    SkeletonDisposition,
    _append_edict_and_snapshot_in_transaction,
    _finalize_attempt_with_edict_in_transaction,
    append_edict_and_snapshot,
    build_decision_edict,
    escalate_disposition,
    persist_edict_and_complete_attempt,
)
from praetor.engine.ids import decision_id_for_attempt, hash_evidence_bundle
from praetor.engine.skeleton import (
    SKELETON_ALERT_ID,
    SKELETON_BUNDLE_HASH,
    SKELETON_EVIDENCE_BUNDLE,
    skeleton_model_judgment,
)
from praetor.engine.timeouts import (
    V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS,
    call_provider_with_latency_tracking,
)
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.excerpt import build_prompt_exemplar_block
from praetor.judgment.prompt import build_judgment_prompt_payload_from_excerpt_set
from praetor.judgment.provider import (
    JudgmentProvider,
    JudgmentRequest,
    ProviderMalformedResponseError,
    ProviderOutputTruncatedError,
    ProviderProbeResult,
    ProviderRefusalError,
    ProviderRetryPolicy,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from praetor.judgment.provider_health_breaker import (
    record_provider_production_failure_in_transaction,
)
from praetor.metrics.collector import MetricsCollector
from praetor.metrics.evaluations import (
    init_policy_gate_evaluation_schema,
    record_policy_gate_evaluation,
)
from praetor.metrics.events import (
    BreakerMetricDomain,
    OutcomeMatrixFaultFlag,
    is_llm_failure_fault_flag,
)
from praetor.policy.containment_policy import policy_gate_evaluation_dimensions
from praetor.policy.gate import (
    LATENCY_SLA_EXCEEDED,
    DeferredDirectivePersistConflict,
    evaluate_policy_gate,
    gate_resolved_containment_target,
    persist_deferred_policy_gate_directive_in_transaction,
    skeleton_disposition_from_evaluation,
)
from praetor.policy.state import BreakerDomain, is_breaker_open
from praetor.retrieval.similar_cases import retrieve_similar_case_exemplars
from praetor.state.attempts import (
    AttemptState,
    ProcessingAttempt,
    abort_attempt,
    transition_attempt,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore
from praetor.tickets.contract import (
    StampContractDisposition,
    apply_terminal_stamp_to_disposition,
    stamp_status_allows_edict_append,
)
from praetor.tickets.outbox import StampStatus
from praetor.tickets.stamp import (
    StampBackendOutcome,
    StampBackendResult,
    StampContext,
    TicketStampBackend,
    execute_stamp,
)


class CorrelationFailure(Exception):
    """Walking skeleton: bundle could not be assembled."""


def _resolve_intake_evidence_bundle(
    *,
    correlate: bool,
    evidence_bundle: EvidenceBundle | None,
    sysmon_events: Sequence[Mapping[str, Any]] | None,
    security_events: Sequence[Mapping[str, Any]] | None,
    anchor_time: datetime | None,
    metrics_collector: MetricsCollector | None = None,
) -> tuple[EvidenceBundle | None, bool]:
    if not correlate:
        return None, True
    if evidence_bundle is not None:
        return evidence_bundle, False
    if sysmon_events is not None or security_events is not None:
        from praetor.correlation import correlate_telemetry

        moment = anchor_time or datetime.now(UTC)
        correlated = correlate_telemetry(
            sysmon_events=list(sysmon_events or ()),
            security_events=list(security_events or ()),
            anchor_time=moment,
            metrics=metrics_collector,
        )
        if not correlated.bundle.facts:
            return None, True
        return correlated.bundle, False
    return SKELETON_EVIDENCE_BUNDLE, False


def _record_intake_metrics_after_actuation(
    metrics: MetricsCollector | None,
    conn: sqlite3.Connection,
    *,
    edict: DecisionEdict,
    directive_persisted: bool,
) -> None:
    if metrics is None:
        return
    metrics.record_policy_gate_result(
        proposed=edict.policy_gate_result.proposed_disposition,
        final=edict.final_disposition,
    )
    if directive_persisted:
        metrics.record_containment_directive()
    metrics.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=is_breaker_open(conn, BreakerDomain.CONTAINMENT),
    )
    metrics.record_breaker_state(
        BreakerMetricDomain.PROVIDER_HEALTH,
        is_open=is_breaker_open(conn, BreakerDomain.PROVIDER_HEALTH),
    )


def _record_intake_metrics_bypass_gate(
    metrics: MetricsCollector | None,
    *,
    disposition: Disposition,
    fault_flag: str | None = None,
) -> None:
    if metrics is None:
        return
    metrics.record_disposition(disposition)
    if fault_flag is not None and is_llm_failure_fault_flag(fault_flag):
        metrics.record_llm_failure(fault_flag)


def _record_stamp_metrics(
    metrics: MetricsCollector | None,
    stamp_status: StampStatus,
) -> None:
    if metrics is None:
        return
    metrics.record_stamp_status(stamp_status)


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
        max_provider_latency_seconds: int = (
            V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS
        ),
        evidence_bundle: EvidenceBundle | None = None,
        sysmon_events: Sequence[Mapping[str, Any]] | None = None,
        security_events: Sequence[Mapping[str, Any]] | None = None,
        anchor_time: datetime | None = None,
        metrics_collector: MetricsCollector | None = None,
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
            max_provider_latency_seconds=max_provider_latency_seconds,
            evidence_bundle=evidence_bundle,
            sysmon_events=sysmon_events,
            security_events=security_events,
            anchor_time=anchor_time,
            metrics_collector=metrics_collector,
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
    max_provider_latency_seconds: int = V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS,
    evidence_bundle: EvidenceBundle | None = None,
    sysmon_events: Sequence[Mapping[str, Any]] | None = None,
    security_events: Sequence[Mapping[str, Any]] | None = None,
    anchor_time: datetime | None = None,
    metrics_collector: MetricsCollector | None = None,
) -> IntakeResult:
    """Run one alert intake; caller must have completed startup recovery."""
    snapshot = fetch_active_snapshot(store.conn)
    if snapshot is None:
        msg = "active org config required for intake"
        raise RuntimeError(msg)
    snap_hash = org_config_snapshot_hash or snapshot.snapshot_hash

    resolved_bundle, correlation_failed = _resolve_intake_evidence_bundle(
        correlate=correlate,
        evidence_bundle=evidence_bundle,
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=anchor_time,
        metrics_collector=metrics_collector,
    )
    if correlation_failed:
        alloc = store.allocate_attempt(
            alert_identity=alert_identity,
            evidence_bundle_hash=SKELETON_BUNDLE_HASH,
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
        return _finish_correlation_failure(
            store, attempt, metrics_collector=metrics_collector
        )

    assert resolved_bundle is not None
    from praetor.correlation.excerpts import build_correlation_prompt_excerpts

    bundle_hash = hash_evidence_bundle(resolved_bundle)
    excerpt_set = build_correlation_prompt_excerpts(resolved_bundle)

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

    decision_id = decision_id_for_attempt(
        alert_identity=attempt.alert_identity,
        evidence_bundle_hash_value=bundle_hash,
        org_config_snapshot_hash=snap_hash,
        processing_attempt_identity=attempt.processing_attempt_identity,
    )

    verbatim = fetch_verbatim_render_text(store.conn, snap_hash)
    if enforce_config_budget:
        if (
            verbatim is not None
            and verbatim_character_count(verbatim) > HARD_CONFIG_CHARACTER_BUDGET
        ):
            return _finish_config_over_budget(
                store,
                attempt,
                judgment_provider,
                metrics_collector=metrics_collector,
            )

    evidence_facts = [fact.model_dump(mode="python") for fact in resolved_bundle.facts]
    exemplars = retrieve_similar_case_exemplars(
        store.conn,
        evidence_facts=evidence_facts,
        exclude_decision_id=decision_id,
    )
    exemplar_block = build_prompt_exemplar_block(exemplars) if exemplars else None
    prompt_payload = build_judgment_prompt_payload_from_excerpt_set(
        excerpt_set=excerpt_set,
        evidence_bundle_hash=bundle_hash,
        org_config_snapshot_hash=snap_hash,
        org_config_verbatim=verbatim or "",
        exemplar_block=exemplar_block,
    )
    request = JudgmentRequest(
        scenario_id=alert_identity,
        payload=prompt_payload,
        evidence_bundle=resolved_bundle,
    )
    try:
        tracked = call_provider_with_latency_tracking(
            judgment_provider,
            request,
            retry_policy=provider_retry_policy,
            max_latency_seconds=max_provider_latency_seconds,
        )
    except (ProviderMalformedResponseError, ProviderOutputTruncatedError):
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=OutcomeMatrixFaultFlag.PROVIDER_MALFORMED_JSON.value,
            metrics_collector=metrics_collector,
        )
    except ProviderTimeoutError:
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT.value,
            metrics_collector=metrics_collector,
        )
    except ProviderRefusalError:
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=OutcomeMatrixFaultFlag.PROVIDER_REFUSAL.value,
            metrics_collector=metrics_collector,
        )
    except ProviderUnavailableError:
        return _finish_provider_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE.value,
            metrics_collector=metrics_collector,
        )
    except AgenticEvidenceGatheringFailedError:
        return _finish_system_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED.value,
            metrics_collector=metrics_collector,
        )
    calls = getattr(judgment_provider, "calls", 0)
    judgment = tracked.judgment

    if tracked.sla_exceeded:
        return _finish_system_fault(
            store,
            attempt,
            judgment_provider,
            fault_flag=LATENCY_SLA_EXCEEDED,
            judgment=judgment,
            calls=calls,
            metrics_collector=metrics_collector,
        )

    if not validate_skeleton_citations(judgment, resolved_bundle):
        return _finish_invalid_citation(
            store,
            attempt,
            judgment,
            calls,
            metrics_collector=metrics_collector,
        )

    gate_evaluation = evaluate_policy_gate(
        store.conn,
        judgment=judgment,
        evidence_bundle=resolved_bundle,
        org_snapshot=snapshot,
        alert_identity=attempt.alert_identity,
        decision_id=decision_id,
        persist_directive=False,
    )
    final_disposition, fault_flags, system_fault, proposed_disposition = (
        skeleton_disposition_from_evaluation(gate_evaluation)
    )
    disposition = SkeletonDisposition(
        final_disposition=final_disposition,
        fault_flags=fault_flags,
        system_fault_escalation=system_fault,
        proposed_disposition=proposed_disposition,
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
    if not stamp_status_allows_edict_append(stamp_result.status):
        return IntakeResult(
            decision_id=None,
            edict=None,
            disposition=None,
            fault_flags=(),
            attempt_aborted=False,
            judgment_provider_calls=calls,
        )
    attempt = transition_attempt(
        store.conn, attempt.processing_attempt_identity, AttemptState.STAMP_RESOLVED
    )
    disposition = _stamp_contract_to_skeleton(
        apply_terminal_stamp_to_disposition(
            stamp_result.status,
            pre_stamp_disposition=_skeleton_to_stamp_contract(disposition),
        )
    )
    never_contain = list(gate_evaluation.live_never_contain_entries)
    if not never_contain:
        never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=never_contain,
        stamp_status=stamp_result.status.value,
        ticket_stamp_payload=stamp_result.ticket_payload,
    )
    directive_persisted = False
    init_policy_gate_evaluation_schema(store.conn)
    with critical_transaction(store.conn):
        if (
            gate_evaluation.final_disposition == Disposition.AUTO_CONTAIN
            and gate_evaluation.containment_directive is not None
            and not gate_evaluation.directive_suppressed
        ):
            directive = gate_evaluation.containment_directive
            if directive is None:
                msg = "auto_contain gate evaluation missing containment directive"
                raise RuntimeError(msg)
            target = gate_resolved_containment_target(gate_evaluation)
            try:
                persist_deferred_policy_gate_directive_in_transaction(
                    store.conn,
                    evaluation=gate_evaluation,
                    org_snapshot=snapshot,
                    alert_identity=attempt.alert_identity,
                    target=target,
                )
                directive_persisted = True
            except DeferredDirectivePersistConflict as conflict:
                conflict_disposition = escalate_disposition(
                    proposed=gate_evaluation.proposed_disposition,
                    fault_flag=conflict.fault_flag,
                    system_fault=conflict.system_fault_escalation,
                )
                disposition = _stamp_contract_to_skeleton(
                    apply_terminal_stamp_to_disposition(
                        stamp_result.status,
                        pre_stamp_disposition=_skeleton_to_stamp_contract(
                            conflict_disposition
                        ),
                    )
                )
                never_contain = list(read_live_never_contain_entries(store.conn))
                edict = build_decision_edict(
                    attempt=attempt,
                    judgment=judgment,
                    disposition=disposition,
                    live_never_contain_entries=never_contain,
                    stamp_status=stamp_result.status.value,
                    ticket_stamp_payload=stamp_result.ticket_payload,
                )
        stored = _append_edict_and_snapshot_in_transaction(
            store.conn,
            edict=edict,
            never_contain_entries=never_contain,
        )
        _finalize_attempt_with_edict_in_transaction(store.conn, attempt, stored)
        dimensions = policy_gate_evaluation_dimensions(
            snapshot,
            gate_evaluation.resolved_target,
        )
        record_policy_gate_evaluation(
            store.conn,
            decision_id=stored.decision_id,
            target_type=dimensions.target_type,
            asset_class=dimensions.asset_class,
            proposed=stored.policy_gate_result.proposed_disposition,
            final=stored.final_disposition,
            evaluated_at=datetime.now(UTC),
        )
    _record_intake_metrics_after_actuation(
        metrics_collector,
        store.conn,
        edict=stored,
        directive_persisted=directive_persisted,
    )
    _record_stamp_metrics(metrics_collector, stamp_result.status)
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=stored.final_disposition,
        fault_flags=tuple(stored.fault_flags),
        attempt_aborted=False,
        judgment_provider_calls=calls,
    )


def _skeleton_to_stamp_contract(
    disposition: SkeletonDisposition,
) -> StampContractDisposition:
    return StampContractDisposition(
        final_disposition=disposition.final_disposition,
        fault_flags=list(disposition.fault_flags),
        system_fault_escalation=disposition.system_fault_escalation,
        proposed_disposition=disposition.proposed_disposition,
    )


def _stamp_contract_to_skeleton(
    disposition: StampContractDisposition,
) -> SkeletonDisposition:
    return SkeletonDisposition(
        final_disposition=disposition.final_disposition,
        fault_flags=list(disposition.fault_flags),
        system_fault_escalation=disposition.system_fault_escalation,
        proposed_disposition=disposition.proposed_disposition,
    )


def _finish_correlation_failure(
    store: StateStore,
    attempt: ProcessingAttempt,
    *,
    metrics_collector: MetricsCollector | None = None,
) -> IntakeResult:
    judgment = skeleton_model_judgment(proposed=Disposition.ESCALATE)
    disposition = escalate_disposition(
        proposed=Disposition.ESCALATE,
        fault_flag=OutcomeMatrixFaultFlag.CORRELATION_FAILURE.value,
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
    _record_intake_metrics_bypass_gate(
        metrics_collector,
        disposition=Disposition.ESCALATE,
        fault_flag=OutcomeMatrixFaultFlag.CORRELATION_FAILURE.value,
    )
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=(OutcomeMatrixFaultFlag.CORRELATION_FAILURE.value,),
        attempt_aborted=True,
        judgment_provider_calls=0,
    )


def _finish_config_over_budget(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment_provider: JudgmentProvider,
    *,
    metrics_collector: MetricsCollector | None = None,
) -> IntakeResult:
    judgment = skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)
    disposition = escalate_disposition(
        proposed=Disposition.STANDARD_REVIEW,
        fault_flag=OutcomeMatrixFaultFlag.CONFIG_OVER_BUDGET.value,
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
    _record_intake_metrics_bypass_gate(
        metrics_collector,
        disposition=Disposition.ESCALATE,
        fault_flag=OutcomeMatrixFaultFlag.CONFIG_OVER_BUDGET.value,
    )
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=(OutcomeMatrixFaultFlag.CONFIG_OVER_BUDGET.value,),
        attempt_aborted=False,
        judgment_provider_calls=calls,
    )


def _record_provider_breaker_failure_hook(conn: sqlite3.Connection) -> None:
    snapshot = fetch_active_snapshot(conn)
    if snapshot is None:
        return
    record_provider_production_failure_in_transaction(
        conn,
        policy=snapshot.provider_health_circuit_breaker_policy,
    )


def _finish_provider_fault(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment_provider: JudgmentProvider,
    *,
    fault_flag: str,
    metrics_collector: MetricsCollector | None = None,
) -> IntakeResult:
    return _finish_system_fault(
        store,
        attempt,
        judgment_provider,
        fault_flag=fault_flag,
        metrics_collector=metrics_collector,
        in_transaction_hook=_record_provider_breaker_failure_hook,
        record_provider_breaker_metrics=True,
    )


def _finish_system_fault(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment_provider: JudgmentProvider,
    *,
    fault_flag: str,
    judgment: ModelJudgment | None = None,
    calls: int | None = None,
    metrics_collector: MetricsCollector | None = None,
    in_transaction_hook: Callable[[sqlite3.Connection], None] | None = None,
    record_provider_breaker_metrics: bool = False,
) -> IntakeResult:
    resolved_judgment = judgment or skeleton_model_judgment(
        proposed=Disposition.STANDARD_REVIEW
    )
    proposed = resolved_judgment.proposed_disposition
    disposition = escalate_disposition(
        proposed=proposed,
        fault_flag=fault_flag,
        system_fault=True,
    )
    never_contain = read_live_never_contain_entries(store.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=resolved_judgment,
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
        in_transaction_hook=in_transaction_hook,
    )
    provider_calls = (
        calls if calls is not None else getattr(judgment_provider, "calls", 0)
    )
    _record_intake_metrics_bypass_gate(
        metrics_collector,
        disposition=Disposition.ESCALATE,
        fault_flag=fault_flag,
    )
    if record_provider_breaker_metrics and metrics_collector is not None:
        metrics_collector.record_breaker_state(
            BreakerMetricDomain.PROVIDER_HEALTH,
            is_open=is_breaker_open(store.conn, BreakerDomain.PROVIDER_HEALTH),
        )
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=(fault_flag,),
        attempt_aborted=False,
        judgment_provider_calls=provider_calls,
    )


def _finish_invalid_citation(
    store: StateStore,
    attempt: ProcessingAttempt,
    judgment: ModelJudgment,
    calls: int,
    *,
    metrics_collector: MetricsCollector | None = None,
) -> IntakeResult:
    disposition = escalate_disposition(
        proposed=judgment.proposed_disposition,
        fault_flag=OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value,
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
    _record_intake_metrics_bypass_gate(
        metrics_collector,
        disposition=Disposition.ESCALATE,
        fault_flag=OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value,
    )
    return IntakeResult(
        decision_id=stored.decision_id,
        edict=stored,
        disposition=Disposition.ESCALATE,
        fault_flags=(OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value,),
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
