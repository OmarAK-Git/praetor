"""Provenance-path constants and account corroboration checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.citations import ResolvedEvidenceCitation

SYSMON_EVENT_LOG = "sysmon_event_log"
WINDOWS_SECURITY_LOG = "windows_security_log"
HOST_ID_FIELD = "host_id"
LEDGER_HISTORY = "ledger_history"

_NON_ATTACKER_CONTROLLABLE_PATHS = frozenset({WINDOWS_SECURITY_LOG})
_ATTACKER_CONTROLLABLE_OVERRIDES = frozenset({SYSMON_EVENT_LOG})
_NON_CORROBORATION_ELIGIBLE_PATHS = frozenset({LEDGER_HISTORY})


def _is_corroboration_eligible_provenance(provenance_path: str) -> bool:
    """Return whether ``provenance_path`` may count toward corroboration (DEC-065)."""
    return provenance_path not in _NON_CORROBORATION_ELIGIBLE_PATHS


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
    """Return whether facts satisfy account corroboration (DEC-065 temporary floor).

    Requires at least one corroboration-eligible supporting fact from any
    ``provenance_path``.
    """
    eligible = tuple(
        fact
        for fact in facts
        if _is_corroboration_eligible_provenance(fact.provenance_path)
    )
    return len(eligible) >= 1


def _fact_anchors_host(
    fact: EvidenceFact,
    *,
    target_host_id: str,
) -> bool:
    """Return whether a bundle fact's normalized fields anchor ``target_host_id``."""
    host_id = fact.normalized_fields.get(HOST_ID_FIELD)
    if not isinstance(host_id, str) or not host_id.strip():
        return False
    return host_id.strip() == target_host_id.strip()


def _cited_fact_anchors_host(
    fact: EvidenceFact | None,
    *,
    target_host_id: str,
) -> bool:
    """Return whether a cited fact's normalized fields anchor ``target_host_id``."""
    if fact is None:
        return False
    return _fact_anchors_host(fact, target_host_id=target_host_id)


def meets_host_bundle_corroboration(
    facts: Sequence[EvidenceFact],
    *,
    target_host_id: str,
) -> bool:
    """Return whether host-scoped bundle facts satisfy presence corroboration."""
    eligible_paths = {
        fact.provenance_path
        for fact in facts
        if _is_corroboration_eligible_provenance(fact.provenance_path)
        and _fact_anchors_host(fact, target_host_id=target_host_id)
    }
    return len(eligible_paths) >= 2


def meets_host_cited_enrichment(
    cited: Sequence[ResolvedEvidenceCitation],
    *,
    target_host_id: str,
    facts_by_id: Mapping[str, EvidenceFact],
) -> bool:
    """Return whether target-anchoring cites satisfy source-event enrichment."""
    source_refs = {
        facts_by_id[ref.evidence_id].source_event_reference
        for ref in cited
        if ref.evidence_id in facts_by_id
        and _is_corroboration_eligible_provenance(ref.provenance_path)
        and _cited_fact_anchors_host(
            facts_by_id.get(ref.evidence_id),
            target_host_id=target_host_id,
        )
    }
    return len(source_refs) >= 2


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
        if _is_corroboration_eligible_provenance(ref.provenance_path)
        and _cited_fact_anchors_host(
            facts_by_id.get(ref.evidence_id),
            target_host_id=target_host_id,
        )
    )
    if not anchored:
        return False
    if len(anchored) == 1 and anchored[0].ambiguity_flag:
        return False
    return True
