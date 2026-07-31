"""process_alert_intake must pass the resolved EvidenceBundle into
JudgmentRequest so agentic-mode providers can query it (Task 4 of
docs/superpowers/plans/2026-07-30-agentic-judgment.md)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    WalkingSkeletonEngine,
)
from praetor.engine.skeleton import SKELETON_EVIDENCE_BUNDLE, skeleton_model_judgment
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult


@dataclass
class _CapturingProvider:
    captured: list[JudgmentRequest]

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.captured.append(request)
        return skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        _ = canary_payload
        return ProviderProbeResult(
            success=True,
            provider_name="capturing",
            model_name="capturing",
            metadata={},
        )


def test_process_alert_intake_passes_evidence_bundle_on_request(activated) -> None:
    provider = _CapturingProvider(captured=[])
    engine = WalkingSkeletonEngine(
        store=activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
    )
    bundle = SKELETON_EVIDENCE_BUNDLE
    engine.process_intake(evidence_bundle=bundle)

    assert len(provider.captured) == 1
    assert provider.captured[0].evidence_bundle is not None
    assert provider.captured[0].evidence_bundle.facts == bundle.facts
