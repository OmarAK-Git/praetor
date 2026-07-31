"""Provenance-path constants and account corroboration checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.citations import ResolvedEvidenceCitation

SYSMON_EVENT_LOG = "sysmon_event_log"
WINDOWS_SECURITY_LOG = "windows_security_log"
HOST_ID_FIELD = "host_id"
LEDGER_HISTORY = "ledger_history"

_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG, LEDGER_HISTORY})
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


def _cited_fact_anchors_host(
    fact: EvidenceFact | None,
    *,
    target_host_id: str,
) -> bool:
    """Return whether a cited fact's normalized fields anchor ``target_host_id``."""
    if fact is None:
        return False
    host_id = fact.normalized_fields.get(HOST_ID_FIELD)
    if not isinstance(host_id, str) or not host_id.strip():
        return False
    return host_id.strip() == target_host_id.strip()


def meets_host_cited_corroboration(
    cited: Sequence[ResolvedEvidenceCitation],
    *,
    target_host_id: str,
    facts_by_id: Mapping[str, EvidenceFact],
) -> bool:
    """Return whether target-anchoring cited facts satisfy host corroboration."""
    anchored = tuple(
        ref
        for ref in cited
        if _cited_fact_anchors_host(
            facts_by_id.get(ref.evidence_id),
            target_host_id=target_host_id,
        )
    )
    if len(anchored) == 1 and anchored[0].ambiguity_flag:
        return False
    paths = frozenset(ref.provenance_path for ref in anchored)
    if len(paths) < 2:
        return False
    return any(not is_attacker_controllable_provenance(path) for path in paths)
