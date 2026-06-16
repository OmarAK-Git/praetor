"""Production throughput benchmark for the DEC-053 serialized intake path (Task 35).

Models production ``auto_contain`` SQLite work after a terminal stamp (DEC-053):

1. ``evaluate_policy_gate(..., persist_directive=False)`` — one gate ``BEGIN IMMEDIATE``
   transaction building a *proposed* directive (feed-health + live never-contain).
2. One engine ``BEGIN IMMEDIATE`` transaction persisting the deferred directive
   (idempotency + rate limits + outstanding directive), then appending
   ``never_contain_snapshot`` + ``DecisionEdict`` to the ledger.

No per-alert automated revocation or feed-outbox write occurs on this path; revocation
throughput is measured separately by ``benchmarks/smoke_serialized_path.py``.

Default ``run_serialized_path_*`` uses distinct hosts per iteration (uncontended best
case). See ``run_contended_production_path_pair`` for duplicate-alert suppression.

``burst_separately_measured`` is ``False`` in v1: only sustained rate is measured;
``meets_burst_target_informational`` compares that same sustained rate to the burst
target for planning visibility only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from benchmarks.smoke_serialized_path import provisional_targets_from_conn

from praetor.config.state import fetch_active_snapshot, read_live_never_contain_entries
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.engine.edict import (
    SkeletonDisposition,
    _append_edict_and_snapshot_in_transaction,
    build_decision_edict,
)
from praetor.engine.ids import decision_id_for_attempt, hash_evidence_bundle
from praetor.policy.containment_policy import ContainmentTarget
from praetor.policy.gate import (
    PolicyGateEvaluation,
    evaluate_policy_gate,
    persist_deferred_policy_gate_directive_in_transaction,
)
from praetor.state.attempts import AttemptState, ProcessingAttempt
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore, open_state_store

PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION = 2
BURST_SEPARATELY_MEASURED_V1 = False

PRODUCTION_MEASURED_SUBSYSTEMS: tuple[str, ...] = (
    "policy_gate_feed_health_check",
    "policy_gate_live_never_contain_check",
    "policy_gate_proposed_directive_build",
    "engine_deferred_directive_persist",
    "engine_idempotency_insert",
    "engine_rate_limit_update",
    "ledger_previous_hash_lookup",
    "ledger_hash_and_insert",
)

# Back-compat alias for tests referencing the old name.
MEASURED_SUBSYSTEMS = PRODUCTION_MEASURED_SUBSYSTEMS


@dataclass(frozen=True)
class SerializedPathBenchmarkResult:
    """Throughput result for the DEC-053 production serialized path."""

    operations: int
    elapsed_seconds: float
    sustained_alerts_per_minute: float
    target_sustained: int
    target_burst: int
    meets_sustained_target: bool
    burst_separately_measured: bool
    meets_burst_target_informational: bool


def _host_bundle(*, host_id: str, moment: datetime) -> EvidenceBundle:
    evidence_id = f"ev-{host_id}"
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id=evidence_id,
                normalized_fields={"host_id": host_id, "process_name": "cmd.exe"},
                source_event_reference=f"bench:{host_id}",
                raw_source="{}",
                provenance_path="synthetic/benchmark",
                ambiguity_flag=False,
                timestamp=moment,
            )
        ]
    )


def _auto_contain_judgment(bundle: EvidenceBundle) -> ModelJudgment:
    fact = bundle.facts[0]
    return ModelJudgment(
        proposed_disposition=Disposition.AUTO_CONTAIN,
        cited_evidence_refs=[
            CitedEvidenceRef(
                evidence_id=fact.evidence_id,
                field_path="host_id",
            )
        ],
        key_tells=["benchmark"],
        org_config_refs=["containment_policy.default_escalate"],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="benchmark",
        narrative="benchmark",
        model_name="benchmark",
        provider_name="benchmark",
    )


def benchmark_result_from_timing(
    *,
    operations: int,
    elapsed: float,
    target_sustained: int,
    target_burst: int,
) -> SerializedPathBenchmarkResult:
    """Build a result from known timing (used by tests and recorded sample runs)."""
    if elapsed <= 0:
        elapsed = 1e-9
    sustained_rate = (operations / elapsed) * 60.0
    return SerializedPathBenchmarkResult(
        operations=operations,
        elapsed_seconds=elapsed,
        sustained_alerts_per_minute=sustained_rate,
        target_sustained=target_sustained,
        target_burst=target_burst,
        meets_sustained_target=sustained_rate >= float(target_sustained),
        burst_separately_measured=BURST_SEPARATELY_MEASURED_V1,
        meets_burst_target_informational=sustained_rate >= float(target_burst),
    )


def run_one_production_serialized_path_operation(
    store: StateStore,
    org_snapshot: OrgConfigSnapshot,
    *,
    index: int,
    moment: datetime | None = None,
    alert_identity: str | None = None,
    host_id: str | None = None,
) -> PolicyGateEvaluation:
    """Execute one DEC-053 production serialized SQLite cycle."""
    conn = store.conn
    when = moment or datetime.now(UTC)
    alert_id = alert_identity if alert_identity is not None else f"BENCH-{index:06d}"
    host = host_id if host_id is not None else f"ws-bench-{index:06d}"
    attempt_identity = f"{index:06d}"
    bundle = _host_bundle(host_id=host, moment=when)
    bundle_hash = hash_evidence_bundle(bundle)
    judgment = _auto_contain_judgment(bundle)
    decision_id = decision_id_for_attempt(
        alert_identity=alert_id,
        evidence_bundle_hash_value=bundle_hash,
        org_config_snapshot_hash=org_snapshot.snapshot_hash,
        processing_attempt_identity=attempt_identity,
    )

    evaluation = evaluate_policy_gate(
        conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity=alert_id,
        decision_id=decision_id,
        now=when,
        persist_directive=False,
    )
    if evaluation.final_disposition != Disposition.AUTO_CONTAIN:
        msg = (
            "benchmark iteration expected AUTO_CONTAIN, got "
            f"{evaluation.final_disposition.value!r}"
        )
        raise RuntimeError(msg)
    if evaluation.containment_directive is None:
        msg = "benchmark iteration missing containment directive"
        raise RuntimeError(msg)

    live_entries = list(evaluation.live_never_contain_entries)
    if not live_entries:
        live_entries = read_live_never_contain_entries(conn)
    attempt = ProcessingAttempt(
        processing_attempt_identity=attempt_identity,
        alert_identity=alert_id,
        evidence_bundle_hash=bundle_hash,
        org_config_snapshot_hash=org_snapshot.snapshot_hash,
        state=AttemptState.READY_TO_APPEND,
        created_at=when,
        updated_at=when,
    )
    disposition = SkeletonDisposition(
        final_disposition=evaluation.final_disposition,
        fault_flags=list(evaluation.fault_flags),
        system_fault_escalation=evaluation.system_fault_escalation,
        proposed_disposition=evaluation.proposed_disposition,
    )
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=live_entries,
        stamp_status="succeeded",
        ticket_stamp_payload={"benchmark": True},
    )

    with critical_transaction(conn):
        if not evaluation.directive_suppressed:
            directive = evaluation.containment_directive
            target = ContainmentTarget(
                target_type=directive.target_type.value,
                target_id=directive.target_id,
                scope=directive.scope,
            )
            persist_deferred_policy_gate_directive_in_transaction(
                conn,
                evaluation=evaluation,
                org_snapshot=org_snapshot,
                alert_identity=alert_id,
                target=target,
                now=when,
            )
        _append_edict_and_snapshot_in_transaction(
            conn,
            edict=edict,
            never_contain_entries=live_entries,
        )

    return evaluation


def run_one_serialized_path_operation(
    store: StateStore,
    org_snapshot: OrgConfigSnapshot,
    *,
    index: int,
    moment: datetime | None = None,
) -> PolicyGateEvaluation:
    """Alias for the uncontended distinct-host production path iteration."""
    return run_one_production_serialized_path_operation(
        store,
        org_snapshot,
        index=index,
        moment=moment,
    )


def run_contended_production_path_pair(
    store: StateStore,
    org_snapshot: OrgConfigSnapshot,
    *,
    moment: datetime | None = None,
) -> tuple[PolicyGateEvaluation, PolicyGateEvaluation]:
    """Two DEC-053 commits for same alert+host; second suppresses directive."""
    when = moment or datetime.now(UTC)
    shared_host = "ws-contended"
    shared_alert = "BENCH-CONTENDED"
    first = run_one_production_serialized_path_operation(
        store,
        org_snapshot,
        index=0,
        moment=when,
        alert_identity=shared_alert,
        host_id=shared_host,
    )
    second = run_one_production_serialized_path_operation(
        store,
        org_snapshot,
        index=1,
        moment=when,
        alert_identity=shared_alert,
        host_id=shared_host,
    )
    return first, second


def run_serialized_path_benchmark(
    db_path: Path,
    *,
    operations: int = 30,
) -> SerializedPathBenchmarkResult:
    """Run DEC-053 production-path operations and compare to active config targets."""
    store = open_state_store(db_path)
    try:
        snapshot = fetch_active_snapshot(store.conn)
        if snapshot is None:
            msg = "serialized path benchmark requires an active org config snapshot"
            raise ValueError(msg)
        target_sustained, target_burst = provisional_targets_from_conn(store.conn)
        start = time.perf_counter()
        for index in range(operations):
            run_one_serialized_path_operation(store, snapshot, index=index)
        elapsed = time.perf_counter() - start
    finally:
        store.close()
    return benchmark_result_from_timing(
        operations=operations,
        elapsed=elapsed,
        target_sustained=target_sustained,
        target_burst=target_burst,
    )


def run_serialized_path_for_store(
    store: StateStore,
    *,
    operations: int,
) -> SerializedPathBenchmarkResult:
    """Benchmark against an already-open store with active org config."""
    snapshot = fetch_active_snapshot(store.conn)
    if snapshot is None:
        msg = "serialized path benchmark requires an active org config snapshot"
        raise ValueError(msg)
    target_sustained, target_burst = provisional_targets_from_conn(store.conn)
    start = time.perf_counter()
    for index in range(operations):
        run_one_serialized_path_operation(store, snapshot, index=index)
    elapsed = time.perf_counter() - start
    return benchmark_result_from_timing(
        operations=operations,
        elapsed=elapsed,
        target_sustained=target_sustained,
        target_burst=target_burst,
    )
