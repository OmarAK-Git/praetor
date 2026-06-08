"""Walking-skeleton adapter for shared citation validation."""

from __future__ import annotations

from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.judgment import ModelJudgment
from praetor.evidence.citations import validate_evidence_citations


def validate_skeleton_citations(
    judgment: ModelJudgment,
    evidence_bundle: EvidenceBundle,
) -> bool:
    """Return True when every cited evidence ref resolves in the bundle."""
    return validate_evidence_citations(judgment, evidence_bundle).valid
