"""Vertex provider stub for the Task 13 provider Protocol."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderProbeResult,
    ProviderUnavailableError,
)


@dataclass(frozen=True)
class VertexProvider:
    model_name: str
    provider_name: str = "vertex"

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        _ = request
        msg = "Vertex provider is a Task 13 stub; live calls are not implemented"
        raise ProviderUnavailableError(msg)

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        _ = canary_payload
        return ProviderProbeResult(
            success=False,
            provider_name=self.provider_name,
            model_name=self.model_name,
            metadata={"status": "stub"},
        )
