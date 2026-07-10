"""Judgment prompt payload construction."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from praetor.judgment.excerpt import (
    PromptExcerptSet,
    PromptExemplarBlock,
    build_prompt_excerpt_set,
    build_prompt_exemplar_block,
)
from praetor.retrieval.similar_cases import retrieve_similar_case_exemplars

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

EXEMPLAR_SCOPE_INSTRUCTIONS = (
    "prompt_exemplar_block lists human-confirmed past cases for illustration only. "
    "Do not cite exemplar_id or source_case_id as evidence; use only "
    "prompt_excerpt_set for evidence-backed citations."
)

EXEMPLAR_INCOMPLETE_WARNING = (
    "Some exemplar summaries are incomplete. Truncated exemplars include an "
    "`incomplete` flag and omitted character count; do not assume omitted text."
)

EXEMPLAR_COMPLETE_NOTICE = "All provided exemplar summaries are complete."


def build_judgment_prompt_payload(
    *,
    evidence_facts: Iterable[Mapping[str, Any]],
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    org_config_verbatim: str,
    exemplars: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, object]:
    excerpt_set = build_prompt_excerpt_set(evidence_facts)
    exemplar_block = build_prompt_exemplar_block(exemplars)
    return build_judgment_prompt_payload_from_excerpt_set(
        excerpt_set=excerpt_set,
        evidence_bundle_hash=evidence_bundle_hash,
        org_config_snapshot_hash=org_config_snapshot_hash,
        org_config_verbatim=org_config_verbatim,
        exemplar_block=exemplar_block,
    )


def build_judgment_prompt_payload_from_excerpt_set(
    *,
    excerpt_set: PromptExcerptSet,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    org_config_verbatim: str,
    exemplar_block: PromptExemplarBlock | None = None,
) -> dict[str, object]:
    content_notice = (
        INCOMPLETE_CONTENT_WARNING
        if excerpt_set.has_incomplete_content
        else COMPLETE_CONTENT_NOTICE
    )
    instructions: dict[str, object] = {
        "evidence_scope": (
            "Use prompt_excerpt_set as the sole provider-facing evidence "
            "content. Never infer from unavailable raw source."
        ),
        "content_notice": content_notice,
        "structured_output": STRUCTURED_OUTPUT_SCHEMA_INSTRUCTIONS,
    }
    if exemplar_block is not None:
        exemplar_notice = (
            EXEMPLAR_INCOMPLETE_WARNING
            if exemplar_block.has_incomplete_content
            else EXEMPLAR_COMPLETE_NOTICE
        )
        instructions["exemplar_scope"] = EXEMPLAR_SCOPE_INSTRUCTIONS
        instructions["exemplar_notice"] = exemplar_notice

    payload: dict[str, object] = {
        "evidence_bundle_hash": evidence_bundle_hash,
        "org_config_snapshot_hash": org_config_snapshot_hash,
        "org_config_verbatim": org_config_verbatim,
        "prompt_excerpt_set": excerpt_set.as_provider_payload(),
        "instructions": instructions,
    }
    if exemplar_block is not None:
        payload["prompt_exemplar_block"] = exemplar_block.as_provider_payload()
    return payload


def build_judgment_prompt_payload_with_similar_cases(
    conn: sqlite3.Connection,
    *,
    evidence_facts: Iterable[Mapping[str, Any]],
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
    org_config_verbatim: str,
    exclude_decision_id: str | None = None,
) -> dict[str, object]:
    """Build a judgment prompt with retrieved human-confirmed similar cases."""
    exemplars = retrieve_similar_case_exemplars(
        conn,
        evidence_facts=evidence_facts,
        exclude_decision_id=exclude_decision_id,
    )
    return build_judgment_prompt_payload(
        evidence_facts=evidence_facts,
        evidence_bundle_hash=evidence_bundle_hash,
        org_config_snapshot_hash=org_config_snapshot_hash,
        org_config_verbatim=org_config_verbatim,
        exemplars=exemplars or None,
    )
