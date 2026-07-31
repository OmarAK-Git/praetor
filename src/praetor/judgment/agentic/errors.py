"""Agentic-pipeline-specific provider errors."""

from __future__ import annotations

from praetor.judgment.provider import ProviderError


class AgenticEvidenceGatheringFailedError(ProviderError):
    """Raised when every Phase 1 source investigator fails for a session."""
