"""Host cited source-event enrichment (DEC-066)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.citations import ResolvedEvidenceCitation
from praetor.evidence.provenance import (
    LEDGER_HISTORY,
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    meets_host_cited_enrichment,
)

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
TARGET_HOST = "ws-01"


def _fact(
    evidence_id: str,
    provenance_path: str,
    *,
    host_id: str | None = TARGET_HOST,
    source_event_reference: str | None = None,
) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"host_id": host_id} if host_id is not None else {},
        source_event_reference=source_event_reference or f"syn:{evidence_id}",
        raw_source="{}",
        provenance_path=provenance_path,
        ambiguity_flag=False,
        timestamp=NOW,
    )


def _citation(
    *,
    evidence_id: str,
    provenance_path: str,
    field_path: str = "host_id",
    value: str = TARGET_HOST,
) -> ResolvedEvidenceCitation:
    return ResolvedEvidenceCitation(
        evidence_id=evidence_id,
        field_path=field_path,
        value=value,
        ambiguity_flag=False,
        provenance_path=provenance_path,
    )


def _check(
    cited: tuple[ResolvedEvidenceCitation, ...],
    *facts: EvidenceFact,
) -> bool:
    return meets_host_cited_enrichment(
        cited,
        target_host_id=TARGET_HOST,
        facts_by_id={fact.evidence_id: fact for fact in facts},
    )


def test_two_distinct_source_events_same_path_enrich() -> None:
    a = _fact("a", SYSMON_EVENT_LOG, source_event_reference="sysmon:1:100")
    b = _fact("b", SYSMON_EVENT_LOG, source_event_reference="sysmon:1:200")
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(evidence_id="b", provenance_path=SYSMON_EVENT_LOG),
    )
    assert _check(cited, a, b) is True


def test_single_cited_event_fails_enrichment() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG)
    security = _fact("b", WINDOWS_SECURITY_LOG)
    cited = (_citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),)
    assert _check(cited, sysmon, security) is False


def test_ledger_history_cite_does_not_count() -> None:
    ledger = _fact("a", LEDGER_HISTORY)
    sysmon = _fact("b", SYSMON_EVENT_LOG, source_event_reference="sysmon:1:100")
    security = _fact("c", WINDOWS_SECURITY_LOG, source_event_reference="sec:4624:1")
    cited = (
        _citation(evidence_id="a", provenance_path=LEDGER_HISTORY),
        _citation(evidence_id="b", provenance_path=SYSMON_EVENT_LOG),
    )
    assert _check(cited, ledger, sysmon, security) is False
