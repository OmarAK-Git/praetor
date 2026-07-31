"""process_alert_intake must map AgenticEvidenceGatheringFailedError to the
agentic_evidence_gathering_failed Outcome Matrix row (DEC-064), mirroring
provider_unavailable (DEC-061) but without tripping the provider-health breaker."""

from __future__ import annotations

from dataclasses import dataclass

from tests.engine.helpers import (
    assert_edict_snapshot_pairing,
    assert_outcome_matrix_edict,
)

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult
from praetor.judgment.provider_health_breaker import read_provider_health_metrics
from praetor.metrics.events import OutcomeMatrixFaultFlag


@dataclass
class _AlwaysFailsAgenticProvider:
    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        raise AgenticEvidenceGatheringFailedError("all sources failed")

    def probe(self, canary_payload: object) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=False, provider_name="agentic", model_name="agentic", metadata={}
        )


def test_intake_escalates_on_agentic_evidence_gathering_failure(activated) -> None:
    result = process_alert_intake(
        activated,
        judgment_provider=_AlwaysFailsAgenticProvider(),
        stamp_backend=SucceedingStampBackend(),
        alert_identity="engine-agentic-evidence-gathering-failed",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=[OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED.value],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_agentic_evidence_gathering_failed_does_not_trip_breaker(activated) -> None:
    before = read_provider_health_metrics(activated.conn).production_failure_total
    provider = _AlwaysFailsAgenticProvider()

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="engine-agentic-evidence-gathering-failed-breaker",
    )

    assert result.edict is not None
    after = read_provider_health_metrics(activated.conn).production_failure_total
    assert after == before
