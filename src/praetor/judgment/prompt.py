"""Judgment prompt payload construction."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from praetor.judgment.excerpt import (
    PromptExcerptSet,
    build_prompt_excerpt_set,
)

STRUCTURED_OUTPUT_SCHEMA_INSTRUCTIONS = (
    "Return only JSON that validates as praetor.contracts.judgment.ModelJudgment. "
    "Do not include markdown, prose outside JSON, or citations to evidence IDs and "
    "field paths that are absent from prompt_excerpt_set."
)

INCOMPLETE_CONTENT_WARNING = (
    "Some evidence excerpts are incomplete. Truncated excerpts include an "
    "`incomplete` flag and omitted character count; do not assume omitted text."
)

COMPLETE_CONTENT_NOTICE = "All provided evidence excerpts are complete."


def build_judgment_prompt_payload(
    *,
    evidence_facts: Iterable[Mapping[str, Any]],
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    org_config_verbatim: str,
) -> dict[str, object]:
    excerpt_set = build_prompt_excerpt_set(evidence_facts)
    return build_judgment_prompt_payload_from_excerpt_set(
        excerpt_set=excerpt_set,
        evidence_bundle_hash=evidence_bundle_hash,
        org_config_snapshot_hash=org_config_snapshot_hash,
        org_config_verbatim=org_config_verbatim,
    )


def build_judgment_prompt_payload_from_excerpt_set(
    *,
    excerpt_set: PromptExcerptSet,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    org_config_verbatim: str,
) -> dict[str, object]:
    content_notice = (
        INCOMPLETE_CONTENT_WARNING
        if excerpt_set.has_incomplete_content
        else COMPLETE_CONTENT_NOTICE
    )
    return {
        "evidence_bundle_hash": evidence_bundle_hash,
        "org_config_snapshot_hash": org_config_snapshot_hash,
        "org_config_verbatim": org_config_verbatim,
        "prompt_excerpt_set": excerpt_set.as_provider_payload(),
        "instructions": {
            "evidence_scope": (
                "Use prompt_excerpt_set as the sole provider-facing evidence "
                "content. Never infer from unavailable raw source."
            ),
            "content_notice": content_notice,
            "structured_output": STRUCTURED_OUTPUT_SCHEMA_INSTRUCTIONS,
        },
    }
