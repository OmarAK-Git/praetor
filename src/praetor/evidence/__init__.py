"""Evidence utilities."""

from praetor.evidence.citations import (
    EvidenceCitationValidationResult,
    ResolvedEvidenceCitation,
    validate_evidence_citations,
)
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    distinct_provenance_paths,
    meets_account_corroboration,
)

__all__ = [
    "EvidenceCitationValidationResult",
    "ResolvedEvidenceCitation",
    "SYSMON_EVENT_LOG",
    "WINDOWS_SECURITY_LOG",
    "distinct_provenance_paths",
    "meets_account_corroboration",
    "validate_evidence_citations",
]
