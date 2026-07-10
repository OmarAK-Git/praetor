"""Retrieve human-confirmed similar cases for judgment prompt exemplars."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from praetor.annotations.precedent import (
    HumanConfirmedPrecedent,
    fetch_human_confirmed_precedents,
)
from praetor.judgment.excerpt import MAX_PROMPT_EXEMPLARS
from praetor.retrieval.ranking import (
    extract_query_tokens,
    rank_precedents_by_similarity,
)


def retrieve_similar_case_exemplars(
    conn: sqlite3.Connection,
    *,
    evidence_facts: Iterable[Mapping[str, Any]],
    exclude_decision_id: str | None = None,
    limit: int = MAX_PROMPT_EXEMPLARS,
) -> tuple[dict[str, Any], ...]:
    """Return exemplar records for ``build_prompt_exemplar_block``."""
    precedents = fetch_human_confirmed_precedents(conn)
    if exclude_decision_id is not None:
        precedents = [
            precedent
            for precedent in precedents
            if precedent.decision_id != exclude_decision_id
        ]

    query_tokens = extract_query_tokens(evidence_facts)
    ranked = rank_precedents_by_similarity(precedents, query_tokens)
    selected = ranked[:limit]
    return tuple(_precedent_to_exemplar(precedent) for precedent in selected)


def _precedent_to_exemplar(precedent: HumanConfirmedPrecedent) -> dict[str, Any]:
    return {
        "exemplar_id": f"precedent-{precedent.annotation_id}",
        "source_case_id": precedent.alert_reference,
        "summary": precedent.summary,
        "disposition": precedent.final_disposition,
    }
