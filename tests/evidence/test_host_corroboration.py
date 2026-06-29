"""Host cited-evidence corroboration floor (DEC-059 / V2-011)."""

from __future__ import annotations

from praetor.evidence.citations import ResolvedEvidenceCitation
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    is_attacker_controllable_provenance,
    meets_host_cited_corroboration,
)


def _citation(
    *,
    evidence_id: str,
    provenance_path: str,
    ambiguity_flag: bool = False,
) -> ResolvedEvidenceCitation:
    return ResolvedEvidenceCitation(
        evidence_id=evidence_id,
        field_path="host_id",
        value="ws-01",
        ambiguity_flag=ambiguity_flag,
        provenance_path=provenance_path,
    )


def test_windows_security_log_not_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(WINDOWS_SECURITY_LOG) is False


def test_sysmon_is_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance(SYSMON_EVENT_LOG) is True


def test_unknown_provenance_defaults_attacker_controllable() -> None:
    assert is_attacker_controllable_provenance("future_normalizer") is True


def test_single_provenance_fails() -> None:
    cited = (_citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),)
    assert meets_host_cited_corroboration(cited) is False


def test_two_attacker_controllable_paths_fail() -> None:
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(evidence_id="b", provenance_path="synthetic/walking_skeleton"),
    )
    assert meets_host_cited_corroboration(cited) is False


def test_sysmon_plus_security_passes() -> None:
    cited = (
        _citation(evidence_id="a", provenance_path=SYSMON_EVENT_LOG),
        _citation(evidence_id="b", provenance_path=WINDOWS_SECURITY_LOG),
    )
    assert meets_host_cited_corroboration(cited) is True


def test_sole_ambiguous_cited_fact_fails() -> None:
    cited = (
        _citation(
            evidence_id="a",
            provenance_path=SYSMON_EVENT_LOG,
            ambiguity_flag=True,
        ),
    )
    assert meets_host_cited_corroboration(cited) is False


def test_ambiguity_on_one_of_two_corroborated_facts_passes() -> None:
    cited = (
        _citation(
            evidence_id="a",
            provenance_path=SYSMON_EVENT_LOG,
            ambiguity_flag=True,
        ),
        _citation(evidence_id="b", provenance_path=WINDOWS_SECURITY_LOG),
    )
    assert meets_host_cited_corroboration(cited) is True
