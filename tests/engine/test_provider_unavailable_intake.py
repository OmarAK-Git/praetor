"""V2-007: ProviderUnavailable intake disposition and breaker side effects."""

from __future__ import annotations

import pytest
from tests.engine.helpers import (
    assert_edict_snapshot_pairing,
    assert_outcome_matrix_edict,
)

from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.judgment.fake_provider import FakeProvider, FakeProviderMode
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderOutputTruncatedError,
    ProviderUnavailableError,
)
from praetor.judgment.provider_health_breaker import read_provider_health_metrics
from praetor.metrics.events import LLM_FAILURE_FAULT_FLAGS, OutcomeMatrixFaultFlag


def test_provider_unavailable_intake_escalates(activated) -> None:
    provider = FakeProvider(mode=FakeProviderMode.UNAVAILABLE)

    with pytest.raises(ProviderUnavailableError):
        provider.generate_judgment(JudgmentRequest(scenario_id="provider_unavailable"))

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="engine-provider-unavailable",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_unavailable"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)
    assert OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE in LLM_FAILURE_FAULT_FLAGS


def test_provider_unavailable_records_breaker_production_failure(activated) -> None:
    before = read_provider_health_metrics(activated.conn).production_failure_total
    provider = FakeProvider(mode=FakeProviderMode.UNAVAILABLE)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="engine-provider-unavailable-breaker",
    )

    assert result.edict is not None
    after = read_provider_health_metrics(activated.conn).production_failure_total
    assert after == before + 1


class _TruncatingProvider:
    def generate_judgment(self, request: JudgmentRequest):
        raise ProviderOutputTruncatedError("vertex output truncated: finishReason=MAX_TOKENS")


def test_provider_truncated_intake_escalates_as_malformed(activated) -> None:
    result = process_alert_intake(
        activated,
        judgment_provider=_TruncatingProvider(),
        stamp_backend=SucceedingStampBackend(),
        alert_identity="engine-provider-truncated",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_malformed_json"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)
