"""Host cited-evidence corroboration floor (DEC-059 / V2-011)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.citations import ResolvedEvidenceCitation
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    is_attacker_controllable_provenance,
    meets_host_cited_corroboration,
)

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
TARGET_HOST = "ws-01"


def _fact(
    evidence_id: str,
    provenance_path: str,
    *,
    host_id: str | None = TARGET_HOST,
    ambiguity_flag: bool = False,
    extra_fields: dict[str, object] | None = None,
) -> EvidenceFact:
    fields: dict[str, object] = dict(extra_fields or {})
    if host_id is not None:
        fields["host_id"] = host_id
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields=fields,
        source_event_reference=f"syn:{evidence_id}",
        raw_source="{}",
        provenance_path=provenance_path,
        ambiguity_flag=ambiguity_flag,
        timestamp=NOW,
    )


def _citation(
    *,
    evidence_id: str,
    provenance_path: str,
    ambiguity_flag: bool = False,
    field_path: str = "host_id",
    value: str = TARGET_HOST,
) -> ResolvedEvidenceCitation:
    return ResolvedEvidenceCitation(
        evidence_id=evidence_id,
        field_path=field_path,
        value=value,
        ambiguity_flag=ambiguity_flag,
        provenance_path=provenance_path,
    )


def _check(
    cited: tuple[ResolvedEvidenceCitation, ...],
    *facts: EvidenceFact,
) -> bool:
    return meets_host_cited_corroboration(
        cited,
        target_host_id=TARGET_HOST,
        facts_by_id={fact.evidence_id: fact for fact in facts},
    )


def test_windows_security_log_not_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(WINDOWS_SECURITY_LOG) is False


def test_sysmon_is_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(SYSMON_EVENT_LOG) is True


def test_unknown_provenance_defaults_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance("future_normalizer") is True


def test_single_provenance_passes() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG)
    cited = (_citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),)
    assert _check(cited, sysmon) is True


def test_two_attacker_controllable_paths_pass() -> None:
    a = _fact("a", SYSMON_EVENT_LOG)
    b = _fact("b", "synthetic/walking_skeleton")
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(evidence_id="b", provenance_path="synthetic/walking_skeleton"),
    )
    assert _check(cited, a, b) is True


def test_sysmon_plus_security_same_host_passes() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG)
    security = _fact("b", WINDOWS_SECURITY_LOG)
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(evidence_id="b", provenance_path=WINDOWS_SECURITY_LOG),
    )
    assert _check(cited, sysmon, security) is True


def test_security_without_host_id_does_not_corroborate_target() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG)
    security = _fact(
        "b",
        WINDOWS_SECURITY_LOG,
        host_id=None,
        extra_fields={"event_id": 4624},
    )
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(
            evidence_id="b",
            provenance_path=WINDOWS_SECURITY_LOG,
            field_path="event_id",
            value=4624,
        ),
    )
    assert _check(cited, sysmon, security) is True


def test_sole_ambiguous_cited_fact_fails() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG, ambiguity_flag=True)
    cited = (
        _citation(
            evidence_id="a",
            provenance_path=SYSMON_EVENT_LOG,
            ambiguity_flag=True,
        ),
    )
    assert _check(cited, sysmon) is False


def test_ambiguity_on_one_of_two_target_anchoring_facts_passes() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG, ambiguity_flag=True)
    security = _fact("b", WINDOWS_SECURITY_LOG)
    cited = (
        _citation(
            evidence_id="a",
            provenance_path=SYSMON_EVENT_LOG,
            ambiguity_flag=True,
        ),
        _citation(evidence_id="b", provenance_path=WINDOWS_SECURITY_LOG),
    )
    assert _check(cited, sysmon, security) is True


def test_non_target_host_citation_does_not_count() -> None:
    sysmon = _fact("a", SYSMON_EVENT_LOG, host_id=TARGET_HOST)
    other_host = _fact("b", WINDOWS_SECURITY_LOG, host_id="ws-other")
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(evidence_id="b", provenance_path=WINDOWS_SECURITY_LOG),
    )
    assert _check(cited, sysmon, other_host) is True


def test_sole_ledger_history_does_not_corroborate() -> None:
    ledger = _fact("a", "ledger_history")
    cited = (_citation(evidence_id="a", provenance_path="ledger_history"),)
    assert _check(cited, ledger) is False


def test_ledger_history_plus_eligible_cite_corroborates() -> None:
    ledger = _fact("a", "ledger_history")
    sysmon = _fact("b", SYSMON_EVENT_LOG)
    cited = (
        _citation(evidence_id="a", provenance_path="ledger_history"),
        _citation(evidence_id="b", provenance_path=SYSMON_EVENT_LOG),
    )
    assert _check(cited, ledger, sysmon) is True


def test_sole_ambiguous_eligible_cite_fails_after_ledger_filtered() -> None:
    ledger = _fact("a", "ledger_history")
    sysmon = _fact("b", SYSMON_EVENT_LOG, ambiguity_flag=True)
    cited = (
        _citation(evidence_id="a", provenance_path="ledger_history"),
        _citation(
            evidence_id="b",
            provenance_path=SYSMON_EVENT_LOG,
            ambiguity_flag=True,
        ),
    )
    assert _check(cited, ledger, sysmon) is False
