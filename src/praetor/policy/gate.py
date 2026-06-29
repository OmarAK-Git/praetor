"""Deterministic PolicyGate v1."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from praetor.config.emergency import live_never_contain_blocks_containment_authorization
from praetor.config.health_emit import (
    flush_health_alert_batch,
    init_health_alert_emit_schema,
)
from praetor.config.state import (
    fetch_outstanding_unrevoked_directives,
    read_live_never_contain_entries,
)
from praetor.containment.lifecycle import (
    build_proposed_directive_in_transaction,
    insert_outstanding_directive_in_transaction,
)
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.policy import PolicyGateResult
from praetor.evidence.citations import validate_evidence_citations
from praetor.hashing import derive_idempotency_key
from praetor.policy.circuit_breaker import (
    BreakerTripResult,
    is_containment_breaker_open,
    record_containment_success_in_transaction,
    record_rate_limit_failure_in_transaction,
)
from praetor.policy.containment_policy import (
    NEVER_CONTAIN_LIVE_CONFLICT,
    NEVER_CONTAIN_SNAPSHOT,
    POLICY_AMBIGUITY,
    ContainmentTarget,
    PolicyAction,
    evaluate_target_containment_policy,
    extract_account_identity,
    resolve_containment_target,
    target_blocked_by_snapshot,
)
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    AMBIGUOUS_CONTAINMENT_TARGET,
    AMBIGUOUS_TARGET_IDENTITY,
    evaluate_account_containment_eligibility,
)
from praetor.policy.rate_limit import (
    increment_rate_limits_for_target_in_transaction,
    is_rate_limit_exceeded_for_target,
)
from praetor.policy.state import (
    BreakerDomain,
    init_policy_state_schema,
    is_breaker_open,
)
from praetor.revocation.exporter import is_feed_actuation_blocked
from praetor.state.idempotency import (
    fetch_active_idempotency_key,
    insert_active_idempotency_key,
)
from praetor.state.sqlite_guard import (
    critical_transaction,
    require_critical_transaction,
)

INVALID_MODEL_CITATION = "invalid_model_citation"
RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
CONTAINMENT_BREAKER_OPEN = "containment_breaker_open"
PROVIDER_HEALTH_BREAKER_OPEN = "provider_health_breaker_open"
REVOCATION_FEED_UNHEALTHY = "revocation_feed_unhealthy"
LATENCY_SLA_EXCEEDED = "latency_sla_exceeded"
QUEUE_AGING_EXCEEDED = "queue_aging_exceeded"


def _live_never_contain_blocks_authorization(
    live_entries: list[dict[str, object]],
    target: ContainmentTarget,
) -> bool:
    return live_never_contain_blocks_containment_authorization(
        target_type=target.target_type,
        target_id=target.target_id,
        live_entries=live_entries,
    )


class _PolicyGateRollback(Exception):
    def __init__(self, evaluation: PolicyGateEvaluation) -> None:
        self.evaluation = evaluation
        super().__init__()


class DeferredDirectivePersistConflict(Exception):
    """Gate passed at eval time but deferred persist preconditions failed in-band."""

    def __init__(self, fault_flag: str, *, system_fault_escalation: bool) -> None:
        self.fault_flag = fault_flag
        self.system_fault_escalation = system_fault_escalation
        super().__init__(fault_flag)


class _RateLimitRaceLoss(Exception):
    """Emit transaction lost rate-limit race; record failure after rollback."""


@dataclass(frozen=True)
class PolicyGateEvaluation:
    proposed_disposition: Disposition
    final_disposition: Disposition
    fault_flags: list[str]
    system_fault_escalation: bool
    containment_directive: ContainmentDirective | None = None
    directive_suppressed: bool = False
    live_never_contain_entries: tuple[dict[str, object], ...] = ()


def _escalate(
    proposed: Disposition,
    fault_flag: str,
    *,
    system_fault: bool,
) -> PolicyGateEvaluation:
    return PolicyGateEvaluation(
        proposed_disposition=proposed,
        final_disposition=Disposition.ESCALATE,
        fault_flags=[fault_flag],
        system_fault_escalation=system_fault,
    )


def _record_rate_limit_failure(
    conn: sqlite3.Connection,
    org_snapshot: OrgConfigSnapshot,
    *,
    now: datetime,
) -> BreakerTripResult:
    with critical_transaction(conn):
        require_critical_transaction(conn)
        return record_rate_limit_failure_in_transaction(
            conn,
            policy=org_snapshot.containment_circuit_breaker_policy,
            now=now,
        )


def _flush_breaker_trip_alerts(conn: sqlite3.Connection, batch_id: str | None) -> None:
    if batch_id is not None:
        flush_health_alert_batch(conn, batch_id=batch_id)


def _pass_through(judgment: ModelJudgment) -> PolicyGateEvaluation:
    proposed = judgment.proposed_disposition
    return PolicyGateEvaluation(
        proposed_disposition=proposed,
        final_disposition=proposed,
        fault_flags=[],
        system_fault_escalation=False,
    )


def _find_outstanding_by_idempotency_key(
    conn: sqlite3.Connection,
    idempotency_key: str,
    *,
    now: datetime | None = None,
) -> ContainmentDirective | None:
    for directive in fetch_outstanding_unrevoked_directives(conn, now=now):
        if directive.idempotency_key == idempotency_key:
            return directive
    return None


def _persist_auto_contain_emit_in_transaction(
    conn: sqlite3.Connection,
    *,
    directive: ContainmentDirective,
    org_snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
    alert_identity: str,
    key_already_active: bool,
    now: datetime,
) -> ContainmentDirective:
    """Insert idempotency, rate counters, breaker success, and outstanding directive."""
    require_critical_transaction(conn)
    if not key_already_active:
        insert_active_idempotency_key(
            conn,
            idempotency_key=directive.idempotency_key,
            alert_identity=alert_identity,
            target_type=target.target_type,
            target_id=target.target_id,
            scope=target.scope,
        )
    increment_rate_limits_for_target_in_transaction(
        conn,
        snapshot=org_snapshot,
        target=target,
        now=now,
    )
    record_containment_success_in_transaction(
        conn,
        policy=org_snapshot.containment_circuit_breaker_policy,
        now=now,
    )
    return insert_outstanding_directive_in_transaction(conn, directive)


def persist_deferred_policy_gate_directive_in_transaction(
    conn: sqlite3.Connection,
    *,
    evaluation: PolicyGateEvaluation,
    org_snapshot: OrgConfigSnapshot,
    alert_identity: str,
    target: ContainmentTarget,
    now: datetime | None = None,
) -> ContainmentDirective | None:
    """Persist a deferred gate directive after terminal stamp (spec ordering)."""
    directive = evaluation.containment_directive
    if directive is None or evaluation.directive_suppressed:
        return directive
    moment = now or datetime.now(UTC)
    require_critical_transaction(conn)
    feed_policy = org_snapshot.revocation_feed_policy
    propagation = feed_policy.max_revocation_feed_propagation_delay_seconds
    if is_feed_actuation_blocked(
        conn,
        propagation_delay_seconds=propagation,
        now=moment,
    ):
        raise DeferredDirectivePersistConflict(
            REVOCATION_FEED_UNHEALTHY,
            system_fault_escalation=True,
        )
    refreshed_live = read_live_never_contain_entries(conn)
    if _live_never_contain_blocks_authorization(refreshed_live, target):
        raise DeferredDirectivePersistConflict(
            NEVER_CONTAIN_LIVE_CONFLICT,
            system_fault_escalation=False,
        )
    tx_exceeded, _ = is_rate_limit_exceeded_for_target(
        conn,
        snapshot=org_snapshot,
        target=target,
        now=moment,
    )
    if tx_exceeded:
        raise DeferredDirectivePersistConflict(
            RATE_LIMIT_EXCEEDED,
            system_fault_escalation=False,
        )
    key_already_active = (
        fetch_active_idempotency_key(conn, directive.idempotency_key) is not None
    )
    return _persist_auto_contain_emit_in_transaction(
        conn,
        directive=directive,
        org_snapshot=org_snapshot,
        target=target,
        alert_identity=alert_identity,
        key_already_active=key_already_active,
        now=moment,
    )


def evaluate_policy_gate(
    conn: sqlite3.Connection,
    *,
    judgment: ModelJudgment,
    evidence_bundle: EvidenceBundle,
    org_snapshot: OrgConfigSnapshot,
    alert_identity: str,
    decision_id: str,
    now: datetime | None = None,
    provider_health_breaker_open: bool = False,
    latency_sla_exceeded: bool = False,
    queue_aging_exceeded: bool = False,
    persist_directive: bool = True,
    _test_before_emit_transaction: Callable[[], None] | None = None,
) -> PolicyGateEvaluation:
    """Deterministically convert model judgment into final disposition."""
    moment = now or datetime.now(UTC)
    proposed = judgment.proposed_disposition
    init_policy_state_schema(conn)
    init_health_alert_emit_schema(conn)

    if provider_health_breaker_open or is_breaker_open(
        conn, BreakerDomain.PROVIDER_HEALTH
    ):
        return _escalate(
            proposed,
            PROVIDER_HEALTH_BREAKER_OPEN,
            system_fault=True,
        )
    if latency_sla_exceeded:
        return _escalate(proposed, LATENCY_SLA_EXCEEDED, system_fault=True)
    if queue_aging_exceeded:
        return _escalate(proposed, QUEUE_AGING_EXCEEDED, system_fault=True)

    citation_result = validate_evidence_citations(judgment, evidence_bundle)
    if not citation_result.valid:
        return _escalate(proposed, INVALID_MODEL_CITATION, system_fault=True)

    if proposed != Disposition.AUTO_CONTAIN:
        return _pass_through(judgment)

    cited_ids = frozenset(ref.evidence_id for ref in citation_result.resolved)
    target_resolution = resolve_containment_target(
        evidence_bundle,
        cited_ids,
    )
    if target_resolution.ambiguous:
        return _escalate(
            proposed,
            AMBIGUOUS_CONTAINMENT_TARGET,
            system_fault=False,
        )
    target = target_resolution.target
    if target is None:
        return _escalate(proposed, AMBIGUOUS_TARGET_IDENTITY, system_fault=False)

    if target_blocked_by_snapshot(org_snapshot, target):
        return _escalate(proposed, NEVER_CONTAIN_SNAPSHOT, system_fault=False)

    live_entries = read_live_never_contain_entries(conn)
    if _live_never_contain_blocks_authorization(live_entries, target):
        return _escalate(proposed, NEVER_CONTAIN_LIVE_CONFLICT, system_fault=False)

    if target.target_type == "account":
        identity = extract_account_identity(list(evidence_bundle.facts))
        assert identity is not None
        eligibility = evaluate_account_containment_eligibility(
            identity,
            evidence_bundle.facts,
        )
        if not eligibility.authorized:
            return _escalate(proposed, AMBIGUOUS_TARGET_IDENTITY, system_fault=False)
        if not org_snapshot.account_auto_contain_enabled:
            return _escalate(proposed, ACCOUNT_CONTAINMENT_DISABLED, system_fault=False)

    policy_eval = evaluate_target_containment_policy(org_snapshot, target)
    if policy_eval.action == PolicyAction.AMBIGUOUS:
        return _escalate(
            proposed,
            policy_eval.fault_flag or POLICY_AMBIGUITY,
            system_fault=False,
        )
    if policy_eval.action != PolicyAction.ALLOW:
        return _escalate(proposed, POLICY_AMBIGUITY, system_fault=False)

    if is_containment_breaker_open(
        conn,
        policy=org_snapshot.containment_circuit_breaker_policy,
        now=moment,
    ):
        return _escalate(proposed, CONTAINMENT_BREAKER_OPEN, system_fault=False)

    feed_policy = org_snapshot.revocation_feed_policy
    propagation = feed_policy.max_revocation_feed_propagation_delay_seconds
    if is_feed_actuation_blocked(
        conn,
        propagation_delay_seconds=propagation,
        now=moment,
    ):
        return _escalate(proposed, REVOCATION_FEED_UNHEALTHY, system_fault=True)

    idempotency_key = derive_idempotency_key(
        alert_identity,
        target.target_type,
        target.target_id,
        target.scope,
    )
    outstanding = _find_outstanding_by_idempotency_key(
        conn, idempotency_key, now=moment
    )
    if outstanding is not None:
        live_entries = read_live_never_contain_entries(conn)
        return PolicyGateEvaluation(
            proposed_disposition=proposed,
            final_disposition=Disposition.AUTO_CONTAIN,
            fault_flags=[],
            system_fault_escalation=False,
            containment_directive=outstanding,
            directive_suppressed=True,
            live_never_contain_entries=tuple(live_entries),
        )

    exceeded, _scope_key = is_rate_limit_exceeded_for_target(
        conn,
        snapshot=org_snapshot,
        target=target,
        now=moment,
    )
    if exceeded:
        trip = _record_rate_limit_failure(conn, org_snapshot, now=moment)
        _flush_breaker_trip_alerts(conn, trip.health_alert_batch_id)
        return _escalate(proposed, RATE_LIMIT_EXCEEDED, system_fault=False)

    key_already_active = fetch_active_idempotency_key(conn, idempotency_key) is not None

    evidence_refs = [ref.evidence_id for ref in judgment.cited_evidence_refs]
    if _test_before_emit_transaction is not None:
        _test_before_emit_transaction()
    try:
        with critical_transaction(conn):
            require_critical_transaction(conn)
            if is_feed_actuation_blocked(
                conn,
                propagation_delay_seconds=propagation,
                now=moment,
            ):
                raise _PolicyGateRollback(
                    _escalate(proposed, REVOCATION_FEED_UNHEALTHY, system_fault=True)
                )
            refreshed_live = read_live_never_contain_entries(conn)
            if _live_never_contain_blocks_authorization(refreshed_live, target):
                raise _PolicyGateRollback(
                    _escalate(proposed, NEVER_CONTAIN_LIVE_CONFLICT, system_fault=False)
                )
            tx_exceeded, _ = is_rate_limit_exceeded_for_target(
                conn,
                snapshot=org_snapshot,
                target=target,
                now=moment,
            )
            if tx_exceeded:
                raise _RateLimitRaceLoss()

            directive = build_proposed_directive_in_transaction(
                conn,
                decision_id=decision_id,
                alert_identity=alert_identity,
                target=target,
                evidence_refs=evidence_refs,
                org_snapshot=org_snapshot,
                live_never_contain_entries=refreshed_live,
                now=moment,
                supersedes_directive_id=None,
            )
            if persist_directive:
                directive = _persist_auto_contain_emit_in_transaction(
                    conn,
                    directive=directive,
                    org_snapshot=org_snapshot,
                    target=target,
                    alert_identity=alert_identity,
                    key_already_active=key_already_active,
                    now=moment,
                )
    except _RateLimitRaceLoss:
        trip = _record_rate_limit_failure(conn, org_snapshot, now=moment)
        _flush_breaker_trip_alerts(conn, trip.health_alert_batch_id)
        return _escalate(proposed, RATE_LIMIT_EXCEEDED, system_fault=False)
    except _PolicyGateRollback as rollback:
        return rollback.evaluation

    return PolicyGateEvaluation(
        proposed_disposition=proposed,
        final_disposition=Disposition.AUTO_CONTAIN,
        fault_flags=[],
        system_fault_escalation=False,
        containment_directive=directive,
        live_never_contain_entries=tuple(refreshed_live),
    )


def evaluation_to_policy_gate_result(
    evaluation: PolicyGateEvaluation,
) -> PolicyGateResult:
    return PolicyGateResult(
        proposed_disposition=evaluation.proposed_disposition,
        final_disposition=evaluation.final_disposition,
    )


def skeleton_disposition_from_evaluation(
    evaluation: PolicyGateEvaluation,
) -> tuple[Disposition, list[str], bool, Disposition]:
    """Return final, fault_flags, system_fault, proposed for edict builders."""
    return (
        evaluation.final_disposition,
        list(evaluation.fault_flags),
        evaluation.system_fault_escalation,
        evaluation.proposed_disposition,
    )
