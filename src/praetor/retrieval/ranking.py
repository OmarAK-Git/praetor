"""Similar-case ranking contract for human-confirmed precedent retrieval.

Ranking contract (V2-034):
1. Eligibility: only decisions with at least one analyst annotation where
   ``disposition_correct`` is true.
2. Exclusion: the active ``decision_id`` (when provided) is never retrieved.
3. Similarity: token overlap between the current evidence excerpt text and each
   precedent summary (narrative, key tells, benign alternatives, analyst comment).
4. Recency: among equal overlap, prefer the more recently confirmed annotation.
5. Stability: tie-break on ``decision_id`` ascending.
6. Bound: return at most ``MAX_PROMPT_EXEMPLARS`` (3) cases.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from praetor.annotations.precedent import HumanConfirmedPrecedent

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def extract_query_tokens(evidence_facts: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    """Collect normalized tokens from provider-eligible evidence fields."""
    tokens: set[str] = set()
    for fact in evidence_facts:
        tokens.update(_tokens_from_value(fact))
    return frozenset(tokens)


def rank_precedents_by_similarity(
    precedents: Sequence[HumanConfirmedPrecedent],
    query_tokens: frozenset[str],
) -> list[HumanConfirmedPrecedent]:
    """Rank precedents per the V2-034 contract."""
    if not precedents:
        return []

    def sort_key(precedent: HumanConfirmedPrecedent) -> tuple[int, float, str]:
        overlap = len(query_tokens & _tokens_from_text(precedent.summary))
        return (-overlap, -precedent.confirmed_at.timestamp(), precedent.decision_id)

    return sorted(precedents, key=sort_key)


def _tokens_from_value(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return {
            token
            for key, item in value.items()
            if key != "raw_source"
            for token in _tokens_from_value(item)
        }
    if isinstance(value, list | tuple):
        return {token for item in value for token in _tokens_from_value(item)}
    return set(_tokens_from_text(_stringify(value)))


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _tokens_from_text(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(text.lower()))
