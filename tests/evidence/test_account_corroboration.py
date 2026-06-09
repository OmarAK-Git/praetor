"""TASK-016: canonical account identity and synthetic provenance tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.evidence.provenance import meets_account_corroboration
from praetor.policy.identity import (
    evaluate_account_containment_eligibility,
    is_sid_backed,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"
NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


def _fact(
    *,
    evidence_id: str,
    provenance_path: str,
    ambiguity_flag: bool = False,
) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"process_name": "cmd.exe"},
        source_event_reference=f"ref:{evidence_id}",
        raw_source="{}",
        provenance_path=provenance_path,
        ambiguity_flag=ambiguity_flag,
        timestamp=NOW,
    )


def _identity(
    *,
    sid: str = "S-1-5-21-1234567890-123456789-123456789-1001",
    ambiguity_flag: bool = False,
) -> CanonicalAccountIdentity:
    return CanonicalAccountIdentity(
        sid=sid,
        domain="CORP",
        account_name="jdoe",
        account_type="user",
        authority_source="windows_security_log",
        ambiguity_flag=ambiguity_flag,
    )


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _facts_from_fixture(name: str) -> list[EvidenceFact]:
    return EvidenceBundle.model_validate(_load_fixture(name)).facts


def test_evidence_fact_missing_provenance_path_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceFact.model_validate(
            {
                "evidence_id": "ev-1",
                "normalized_fields": {},
                "source_event_reference": "sysmon:1",
                "raw_source": "{}",
                "ambiguity_flag": False,
                "timestamp": NOW.isoformat(),
            }
        )


@pytest.mark.parametrize(
    "missing_field",
    [
        "sid",
        "domain",
        "account_name",
        "account_type",
        "authority_source",
        "ambiguity_flag",
    ],
)
def test_canonical_account_identity_requires_all_fields(
    missing_field: str,
) -> None:
    payload = {
        "schema_version": "1",
        "sid": "S-1-5-21-1234567890-123456789-123456789-1001",
        "domain": "CORP",
        "account_name": "jdoe",
        "account_type": "user",
        "authority_source": "windows_security_log",
        "ambiguity_flag": False,
    }
    del payload[missing_field]
    with pytest.raises(ValidationError):
        CanonicalAccountIdentity.model_validate(payload)


def test_sid_absent_identity_cannot_authorize_containment() -> None:
    result = evaluate_account_containment_eligibility(
        _identity(sid=""),
        [
            _fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log"),
            _fact(
                evidence_id="ev-security",
                provenance_path="windows_security_log",
            ),
        ],
    )

    assert result.authorized is False
    assert result.fault_flag == "ambiguous_target_identity"
    assert result.system_fault_escalation is False
    assert result.final_disposition == Disposition.ESCALATE


def test_sid_backed_corroborated_authorizes_containment() -> None:
    payload = _load_fixture("account_eligible_valid.json")
    identity = CanonicalAccountIdentity.model_validate(payload["identity"])
    facts = EvidenceBundle.model_validate({"facts": payload["facts"]}).facts

    result = evaluate_account_containment_eligibility(identity, facts)

    assert result.authorized is True
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.fault_flag is None
    assert result.system_fault_escalation is False


def test_sid_backed_insufficient_not_flagged_escalates() -> None:
    result = evaluate_account_containment_eligibility(
        _identity(ambiguity_flag=False),
        [_fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log")],
    )

    assert result.authorized is False
    assert result.fault_flag == "ambiguous_target_identity"
    assert result.system_fault_escalation is False
    assert result.final_disposition == Disposition.ESCALATE


def test_same_provenance_facts_do_not_corroborate() -> None:
    facts = [
        _fact(evidence_id="ev-sysmon-a", provenance_path="sysmon_event_log"),
        _fact(evidence_id="ev-sysmon-b", provenance_path="sysmon_event_log"),
    ]

    assert meets_account_corroboration(facts) is False


def test_sysmon_plus_security_log_satisfies_corroboration() -> None:
    facts = [
        _fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log"),
        _fact(evidence_id="ev-security", provenance_path="windows_security_log"),
    ]

    assert meets_account_corroboration(facts) is True


def test_two_security_logs_do_not_corroborate() -> None:
    facts = [
        _fact(evidence_id="ev-security-a", provenance_path="windows_security_log"),
        _fact(evidence_id="ev-security-b", provenance_path="windows_security_log"),
    ]

    assert meets_account_corroboration(facts) is False


def test_single_and_empty_do_not_corroborate() -> None:
    assert meets_account_corroboration([]) is False
    assert (
        meets_account_corroboration(
            [_fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log")]
        )
        is False
    )


def test_corroboration_requires_windows_security_source() -> None:
    facts = [
        _fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log"),
        _fact(evidence_id="ev-edr", provenance_path="edr_process_telemetry"),
    ]

    assert meets_account_corroboration(facts) is False


def test_whitespace_sid_is_not_sid_backed() -> None:
    identity = _identity(sid="   ")

    assert is_sid_backed(identity) is False

    result = evaluate_account_containment_eligibility(
        identity,
        [
            _fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log"),
            _fact(evidence_id="ev-security", provenance_path="windows_security_log"),
        ],
    )

    assert result.authorized is False
    assert result.fault_flag == "ambiguous_target_identity"
    assert result.system_fault_escalation is False
    assert result.final_disposition == Disposition.ESCALATE


def test_ambiguous_target_insufficient_corroboration_escalates() -> None:
    result = evaluate_account_containment_eligibility(
        _identity(ambiguity_flag=True),
        [_fact(evidence_id="ev-sysmon", provenance_path="sysmon_event_log")],
    )

    assert result.authorized is False
    assert result.fault_flag == "ambiguous_target_identity"
    assert result.system_fault_escalation is False
    assert result.final_disposition == Disposition.ESCALATE


def test_synthetic_fixture_corroboration_pair() -> None:
    facts = _facts_from_fixture("account_corroboration_valid.json")

    assert meets_account_corroboration(facts) is True


def test_synthetic_fixture_same_provenance_rejected() -> None:
    facts = _facts_from_fixture("account_same_provenance.json")

    assert meets_account_corroboration(facts) is False


def test_synthetic_fixture_ambiguous_insufficient_escalates() -> None:
    payload = _load_fixture("account_ambiguous_insufficient.json")
    identity = CanonicalAccountIdentity.model_validate(payload["identity"])
    facts = EvidenceBundle.model_validate({"facts": payload["facts"]}).facts

    result = evaluate_account_containment_eligibility(identity, facts)

    assert result.authorized is False
    assert result.fault_flag == "ambiguous_target_identity"
    assert result.system_fault_escalation is False
    assert result.final_disposition == Disposition.ESCALATE
