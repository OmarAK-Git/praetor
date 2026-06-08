"""Structural evidence citation validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import ModelJudgment

_CITATION_REQUIRED_DISPOSITIONS = frozenset(
    {
        Disposition.ESCALATE,
        Disposition.AUTO_CONTAIN,
    }
)
_PROMPT_EXCLUDED_FIELD_PATHS = frozenset({"raw_source"})
_PROMPT_VISIBLE_METADATA_PATHS = frozenset(
    {
        "source_event_reference",
        "provenance_path",
    }
)


@dataclass(frozen=True)
class ResolvedEvidenceCitation:
    evidence_id: str
    field_path: str
    value: Any
    ambiguity_flag: bool
    provenance_path: str


@dataclass(frozen=True)
class EvidenceCitationValidationResult:
    """Structural citation validation outcome.

    ``resolved`` is authoritative only when ``valid is True``. When ``valid`` is
    False, ``resolved`` may contain refs that resolved before a later failure.
    """

    valid: bool
    resolved: tuple[ResolvedEvidenceCitation, ...]
    errors: tuple[str, ...]


def validate_evidence_citations(
    judgment: ModelJudgment,
    evidence_bundle: EvidenceBundle,
) -> EvidenceCitationValidationResult:
    """Validate model evidence refs against bundle facts and field paths."""
    errors: list[str] = []
    resolved: list[ResolvedEvidenceCitation] = []
    refs = judgment.cited_evidence_refs

    if (
        not refs
        and judgment.proposed_disposition in _CITATION_REQUIRED_DISPOSITIONS
    ):
        errors.append(f"missing_citations:{judgment.proposed_disposition.value}")

    facts_by_id = {fact.evidence_id: fact for fact in evidence_bundle.facts}
    for ref in refs:
        fact = facts_by_id.get(ref.evidence_id)
        if fact is None:
            errors.append(f"missing_evidence_id:{ref.evidence_id}:{ref.field_path}")
            continue

        field_found, value = _resolve_field_path(fact, ref.field_path)
        if not field_found:
            errors.append(f"missing_field_path:{ref.evidence_id}:{ref.field_path}")
            continue

        resolved.append(
            ResolvedEvidenceCitation(
                evidence_id=ref.evidence_id,
                field_path=ref.field_path,
                value=value,
                ambiguity_flag=fact.ambiguity_flag,
                provenance_path=fact.provenance_path,
            )
        )

    return EvidenceCitationValidationResult(
        valid=not errors,
        resolved=tuple(resolved),
        errors=tuple(errors),
    )


def _resolve_field_path(fact: EvidenceFact, field_path: str) -> tuple[bool, Any]:
    if not field_path:
        return False, None
    parts = tuple(field_path.split("."))
    if any(part in _PROMPT_EXCLUDED_FIELD_PATHS for part in parts):
        return False, None

    if parts[0] == "normalized_fields":
        return _resolve_parts(fact.normalized_fields, parts[1:])

    found, value = _resolve_parts(fact.normalized_fields, parts)
    if found:
        return True, value

    if field_path in _PROMPT_VISIBLE_METADATA_PATHS:
        return True, getattr(fact, field_path)

    return False, None


def _resolve_parts(value: Any, parts: tuple[str, ...]) -> tuple[bool, Any]:
    current = value
    for part in parts:
        if isinstance(current, Mapping):
            if part not in current:
                return False, None
            current = current[part]
            continue
        if (
            isinstance(current, Sequence)
            and not isinstance(current, (str, bytes))
            and part.isdecimal()
        ):
            index = int(part)
            if index >= len(current):
                return False, None
            current = current[index]
            continue
        return False, None
    return True, current
