"""Scenario-scoped FakeProvider modes for tests and eval harnesses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderProbeResult,
    ProviderRefusalError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    parse_model_judgment_json,
)


class FakeProviderMode(StrEnum):
    VALID = "valid"
    MALFORMED_JSON = "malformed_json"
    TIMEOUT = "timeout"
    REFUSAL = "refusal"
    UNAVAILABLE = "unavailable"
    AGENTIC_EVIDENCE_GATHERING_FAILED = "agentic_evidence_gathering_failed"
    FABRICATED_CITATION = "fabricated_citation"


@dataclass
class FakeProvider:
    mode: FakeProviderMode = FakeProviderMode.VALID
    scenario_modes: Mapping[str, FakeProviderMode] = field(default_factory=dict)
    proposed_disposition: Disposition = Disposition.STANDARD_REVIEW
    model_name: str = "fake-model"
    calls: int = 0

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.calls += 1
        mode = self.scenario_modes.get(request.scenario_id, self.mode)
        if mode == FakeProviderMode.TIMEOUT:
            raise ProviderTimeoutError("fake provider timeout")
        if mode == FakeProviderMode.REFUSAL:
            raise ProviderRefusalError("fake provider refusal")
        if mode == FakeProviderMode.UNAVAILABLE:
            raise ProviderUnavailableError("fake provider unavailable")
        if mode == FakeProviderMode.AGENTIC_EVIDENCE_GATHERING_FAILED:
            raise AgenticEvidenceGatheringFailedError("fake all-sources-failed")
        if mode == FakeProviderMode.MALFORMED_JSON:
            return parse_model_judgment_json('{"schema_version": "1"')
        if mode == FakeProviderMode.FABRICATED_CITATION:
            return self._judgment_with_refs(
                [
                    CitedEvidenceRef(
                        evidence_id="fabricated-evidence-id",
                        field_path="process_name",
                    )
                ]
            )
        return self._judgment_with_refs(None)

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True,
            provider_name="fake",
            model_name=self.model_name,
            metadata={"canary_seen": bool(canary_payload)},
        )

    def _judgment_with_refs(
        self, refs: list[CitedEvidenceRef] | None
    ) -> ModelJudgment:
        judgment = skeleton_model_judgment(
            proposed=self.proposed_disposition,
            cited_refs=refs,
        )
        raw_json = judgment.model_copy(
            update={
                "model_name": self.model_name,
                "provider_name": "fake",
            }
        ).model_dump_json()
        return parse_model_judgment_json(raw_json)
