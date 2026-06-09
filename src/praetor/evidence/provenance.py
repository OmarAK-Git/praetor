"""Provenance-path constants and account corroboration checks."""

from __future__ import annotations

from collections.abc import Sequence

from praetor.contracts.evidence import EvidenceFact

SYSMON_EVENT_LOG = "sysmon_event_log"
WINDOWS_SECURITY_LOG = "windows_security_log"


def distinct_provenance_paths(facts: Sequence[EvidenceFact]) -> frozenset[str]:
    """Return the distinct provenance paths present in normalized facts."""
    return frozenset(fact.provenance_path for fact in facts)


def meets_account_corroboration(facts: Sequence[EvidenceFact]) -> bool:
    """Return whether facts satisfy v1 Windows/Sysmon account corroboration.

    Requires at least one ``sysmon_event_log`` and one ``windows_security_log``
    fact. Two facts from the same provenance path do not corroborate.
    """
    paths = distinct_provenance_paths(facts)
    return SYSMON_EVENT_LOG in paths and WINDOWS_SECURITY_LOG in paths
