"""Structural citation validation for the walking skeleton."""

from __future__ import annotations

from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment


def validate_skeleton_citations(
    judgment: ModelJudgment,
    catalog: dict[str, dict[str, object]],
) -> bool:
    """Return True when every cited evidence ref resolves in the catalog."""
    for ref in judgment.cited_evidence_refs:
        if not _ref_resolves(ref, catalog):
            return False
    return True


def _ref_resolves(
    ref: CitedEvidenceRef,
    catalog: dict[str, dict[str, object]],
) -> bool:
    fact = catalog.get(ref.evidence_id)
    if fact is None:
        return False
    return ref.field_path in fact
