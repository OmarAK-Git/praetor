"""Provenance-path constants and account corroboration checks."""

from __future__ import annotations

from collections.abc import Sequence

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.citations import ResolvedEvidenceCitation

SYSMON_EVENT_LOG = "sysmon_event_log"
WINDOWS_SECURITY_LOG = "windows_security_log"

_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG})
_ATTACKER_CONTROLLABLE_OVERRIDES = frozenset({SYSMON_EVENT_LOG})


def distinct_provenance_paths(facts: Sequence[EvidenceFact]) -> frozenset[str]:
    """Return the distinct provenance paths present in normalized facts."""
    return frozenset(fact.provenance_path for fact in facts)


def is_attacker_controllable_provenance(provenance_path: str) -> bool:
    """Return whether a provenance path is attacker-controllable (contracts §12a)."""
    if provenance_path in _NON_ATTACKER_CONTROLLABLE_PATHS:
        return False
    if provenance_path in _ATTACKER_CONTROLLABLE_OVERRIDES:
        return True
    return True


def meets_account_corroboration(facts: Sequence[EvidenceFact]) -> bool:
    """Return whether facts satisfy v1 Windows/Sysmon account corroboration.

    Requires at least one ``sysmon_event_log`` and one ``windows_security_log``
    fact. Two facts from the same provenance path do not corroborate.
    """
    paths = distinct_provenance_paths(facts)
    return SYSMON_EVENT_LOG in paths and WINDOWS_SECURITY_LOG in paths


def meets_host_cited_corroboration(
    cited: Sequence[ResolvedEvidenceCitation],
) -> bool:
    """Return whether cited facts satisfy the host auto_contain corroboration floor."""
    if len(cited) == 1 and cited[0].ambiguity_flag:
        return False
    paths = frozenset(ref.provenance_path for ref in cited)
    if len(paths) < 2:
        return False
    return any(not is_attacker_controllable_provenance(path) for path in paths)
