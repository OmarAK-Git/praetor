"""Unit tests for agentic pipeline error types."""

from __future__ import annotations

from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.provider import ProviderError


def test_agentic_evidence_gathering_failed_is_a_provider_error() -> None:
    assert issubclass(AgenticEvidenceGatheringFailedError, ProviderError)
