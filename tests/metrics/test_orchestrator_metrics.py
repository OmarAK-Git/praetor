"""MetricsCollector wiring on the production intake path (Task 28a)."""

from __future__ import annotations

from tests.policy.conftest import (
    auto_contain_judgment,
    host_auto_contain_policy,
    host_bundle,
    persist_snapshot_with_overrides,
)

from praetor.config.state import fetch_active_snapshot
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.judgment.fake_provider import FakeProvider, FakeProviderMode
from praetor.metrics.collector import MetricsCollector
from praetor.metrics.events import (
    LLM_FAILURE_FAULT_FLAGS,
    BreakerMetricDomain,
    OutcomeMatrixFaultFlag,
)
from praetor.tickets.outbox import StampStatus


def test_intake_records_policy_gate_metrics_on_auto_contain(activated) -> None:
    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        activated,
        snapshot,
        containment_policy=host_auto_contain_policy(),
    )
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)
    metrics = MetricsCollector()

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="metrics-auto-contain",
        evidence_bundle=bundle,
        metrics_collector=metrics,
    )

    assert result.disposition == Disposition.AUTO_CONTAIN
    snap = metrics.snapshot()
    assert snap.policy_gate_evaluations_total == 1
    assert snap.policy_gate_override_total == 0
    assert snap.disposition_counts[Disposition.AUTO_CONTAIN.value] == 1
    assert snap.containment_directive_total == 1
    assert snap.breaker_currently_open[BreakerMetricDomain.CONTAINMENT.value] is False
    assert snap.stamp_status_counts[StampStatus.SUCCEEDED.value] == 1


def test_intake_records_policy_gate_override_on_never_contain(activated) -> None:
    bundle = host_bundle(host_id="dc-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)
    metrics = MetricsCollector()

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="metrics-never-contain",
        evidence_bundle=bundle,
        metrics_collector=metrics,
    )

    assert result.disposition == Disposition.ESCALATE
    snap = metrics.snapshot()
    assert snap.policy_gate_evaluations_total == 1
    assert snap.policy_gate_override_total == 1
    assert snap.disposition_counts[Disposition.ESCALATE.value] == 1
    assert snap.containment_directive_total == 0


def test_intake_records_bypass_gate_metrics_on_correlation_failure(activated) -> None:
    metrics = MetricsCollector()
    provider = _CountingJudgmentProvider(
        judgment=auto_contain_judgment(host_bundle(host_id="ws-01"))
    )

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="metrics-corr-fail",
        correlate=False,
        metrics_collector=metrics,
    )

    assert result.disposition == Disposition.ESCALATE
    snap = metrics.snapshot()
    assert snap.policy_gate_evaluations_total == 0
    assert snap.disposition_counts[Disposition.ESCALATE.value] == 1
    assert snap.llm_failure_by_fault_flag == {}


def test_intake_records_provider_unavailable_llm_failure_metric(activated) -> None:
    provider = FakeProvider(mode=FakeProviderMode.UNAVAILABLE)
    metrics = MetricsCollector()

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="metrics-provider-unavailable",
        metrics_collector=metrics,
    )

    assert result.disposition == Disposition.ESCALATE
    snap = metrics.snapshot()
    flag = OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE.value
    assert flag in LLM_FAILURE_FAULT_FLAGS
    assert snap.policy_gate_evaluations_total == 0
    assert snap.llm_failure_by_fault_flag == {flag: 1}
    assert snap.disposition_counts[Disposition.ESCALATE.value] == 1
    assert set(snap.llm_failure_by_fault_flag) <= {
        member.value for member in LLM_FAILURE_FAULT_FLAGS
    }


def test_unknown_stamp_does_not_increment_gate_or_disposition_metrics(
    activated,
) -> None:
    from tests.engine.stamp_fakes import AlwaysTimeoutStampBackend

    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)
    metrics = MetricsCollector()

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AlwaysTimeoutStampBackend(),
        alert_identity="metrics-unknown-stamp",
        evidence_bundle=bundle,
        metrics_collector=metrics,
    )

    assert result.edict is None
    snap = metrics.snapshot()
    assert snap.policy_gate_evaluations_total == 0
    assert snap.containment_directive_total == 0
    assert snap.disposition_counts == {}
