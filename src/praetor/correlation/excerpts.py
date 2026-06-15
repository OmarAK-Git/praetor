"""Prompt excerpt construction for correlated evidence bundles."""

from __future__ import annotations

from typing import Any

from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.judgment.excerpt import PromptExcerptSet, build_prompt_excerpt_set


def fact_to_prompt_mapping(fact: EvidenceFact) -> dict[str, Any]:
    payload = fact.model_dump(mode="json")
    payload["timestamp"] = fact.timestamp.isoformat().replace("+00:00", "Z")
    return payload


def build_correlation_prompt_excerpts(
    bundle: EvidenceBundle,
) -> PromptExcerptSet:
    """Build a provider-facing excerpt set from a correlated bundle."""
    return build_prompt_excerpt_set(
        fact_to_prompt_mapping(fact) for fact in bundle.facts
    )
