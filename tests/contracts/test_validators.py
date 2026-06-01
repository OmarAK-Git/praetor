"""Cross-field and negative validation tests (B-003)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from praetor.contracts.alert import AlertEnvelope
from praetor.contracts.containment import ContainmentDirective, DirectiveStatus, TargetType
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.governance import AnalystAnnotation
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.ledger import DirectiveRevocationRecord, EmergencyNeverContainRecord, RevocationReason

UTC = timezone.utc
NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def test_disposition_rejects_pass() -> None:
    with pytest.raises(ValidationError):
        ModelJudgment.model_validate(
            {
                "schema_version": "1",
                "proposed_disposition": "pass",
                "cited_evidence_refs": [],
                "key_tells": [],
                "org_config_refs": [],
                "benign_alternatives": [],
                "benign_alternatives_ruled_out": [],
                "convergence_reasoning": "",
                "narrative": "",
                "model_name": "m",
                "provider_name": "p",
            }
        )


def test_analyst_annotation_requires_correction_when_incorrect() -> None:
    with pytest.raises(ValidationError):
        AnalystAnnotation(
            disposition_correct=False,
            corrected_disposition=None,
            comment="wrong",
            reviewer_identity="a1",
            timestamp=NOW,
        )


def test_analyst_annotation_forbids_correction_when_correct() -> None:
    with pytest.raises(ValidationError):
        AnalystAnnotation(
            disposition_correct=True,
            corrected_disposition=Disposition.ESCALATE,
            comment="?",
            reviewer_identity="a1",
            timestamp=NOW,
        )


def test_decision_edict_record_type_and_fault_flag(containment_directive, decision_edict: DecisionEdict) -> None:
    assert decision_edict.record_type == "decision_edict"
    assert decision_edict.system_fault_escalation is False
    _ = containment_directive  # fixture ensures directive model exists


def test_containment_directive_rejects_revocation_feed_id(containment_directive: ContainmentDirective) -> None:
    data = containment_directive.model_dump(mode="json")
    data["revocation_feed_id"] = "feed-99"
    with pytest.raises(ValidationError):
        ContainmentDirective.model_validate(data)


def test_containment_directive_max_lifetime(containment_directive: ContainmentDirective) -> None:
    data = containment_directive.model_dump(mode="json")
    data["expires_at"] = (containment_directive.issued_at + timedelta(seconds=301)).isoformat()
    with pytest.raises(ValidationError):
        ContainmentDirective.model_validate(data)


def test_containment_directive_account_requires_sid(containment_directive: ContainmentDirective) -> None:
    data = containment_directive.model_dump(mode="json")
    data["target_type"] = "account"
    data["target_id"] = "not-a-sid"
    with pytest.raises(ValidationError):
        ContainmentDirective.model_validate(data)


def test_emergency_never_contain_max_lifetime(emergency_never_contain_record) -> None:
    data = emergency_never_contain_record.model_dump(mode="json")
    added = emergency_never_contain_record.added_at
    data["expires_at"] = (added + timedelta(hours=49)).isoformat()
    with pytest.raises(ValidationError):
        EmergencyNeverContainRecord.model_validate(data)


def test_revocation_idempotency_key_cleared_only_for_manual() -> None:
    DirectiveRevocationRecord(
        revocation_id="r1",
        directive_id="d1",
        reason=RevocationReason.MANUAL,
        reason_code="manual_revocation",
        triggered_by="soc-lead-1",
        revoked_at=NOW,
        ledger_commit_at=NOW,
        idempotency_key_cleared=True,
    )

    with pytest.raises(ValidationError):
        DirectiveRevocationRecord(
            revocation_id="r2",
            directive_id="d1",
            reason=RevocationReason.SUPERSESSION,
            reason_code="supersession",
            triggered_by="system",
            revoked_at=NOW,
            ledger_commit_at=NOW,
            idempotency_key_cleared=True,
            superseded_by_directive_id="dir-2",
        )

    with pytest.raises(ValidationError):
        DirectiveRevocationRecord(
            revocation_id="r3",
            directive_id="d1",
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            reason_code="never_contain_conflict",
            triggered_by="system",
            revoked_at=NOW,
            ledger_commit_at=NOW,
            idempotency_key_cleared=True,
        )


def test_revocation_supersession_requires_superseded_id() -> None:
    with pytest.raises(ValidationError):
        DirectiveRevocationRecord(
            revocation_id="r1",
            directive_id="d1",
            reason=RevocationReason.SUPERSESSION,
            reason_code="supersession",
            triggered_by="system",
            revoked_at=NOW,
            ledger_commit_at=NOW,
            idempotency_key_cleared=False,
            superseded_by_directive_id=None,
        )


def test_revocation_non_supersession_forbids_superseded_id(directive_revocation_record: DirectiveRevocationRecord) -> None:
    record = directive_revocation_record.model_copy(
        update={
            "reason": RevocationReason.SUPERSESSION,
            "superseded_by_directive_id": "dir-2",
        }
    )
    assert record.reason == RevocationReason.SUPERSESSION
    assert record.superseded_by_directive_id == "dir-2"

    with pytest.raises(ValidationError):
        DirectiveRevocationRecord(
            revocation_id=directive_revocation_record.revocation_id,
            directive_id=directive_revocation_record.directive_id,
            reason=RevocationReason.MANUAL,
            reason_code=directive_revocation_record.reason_code,
            triggered_by=directive_revocation_record.triggered_by,
            revoked_at=directive_revocation_record.revoked_at,
            ledger_commit_at=directive_revocation_record.ledger_commit_at,
            idempotency_key_cleared=directive_revocation_record.idempotency_key_cleared,
            superseded_by_directive_id="dir-2",
        )


def test_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        AlertEnvelope.model_validate({"schema_version": "1", "alert_identity": "A", "unknown": True})


def test_containment_directive_required_fields_present(containment_directive: ContainmentDirective) -> None:
    assert containment_directive.status == DirectiveStatus.PROPOSED
    assert containment_directive.live_never_contain_hash
    assert containment_directive.embedded_never_contain_entries == []
    assert containment_directive.minimum_feed_sequence_at_issue == 1


def test_account_sid_accepted() -> None:
    issued = NOW
    directive = ContainmentDirective(
        directive_id="d",
        decision_id="dec",
        target_type=TargetType.ACCOUNT,
        target_id="S-1-5-21-1-2-3-1001",
        scope="s",
        evidence_refs=[],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=60),
        idempotency_key="k",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.PROPOSED,
        live_never_contain_hash="h",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    assert directive.target_type == TargetType.ACCOUNT


def test_invalid_schema_version_literal_rejected() -> None:
    with pytest.raises(ValidationError):
        AlertEnvelope.model_validate({"schema_version": "2", "alert_identity": "A"})


def test_invalid_record_type_literal_rejected(decision_edict: DecisionEdict) -> None:
    data = decision_edict.model_dump(mode="json")
    data["record_type"] = "not_a_ledger_type"
    with pytest.raises(ValidationError):
        DecisionEdict.model_validate(data)


@pytest.mark.parametrize(
    ("fixture_name", "wrong_record_type"),
    [
        ("decision_edict", "directive_revocation"),
        ("never_contain_snapshot_record", "decision_edict"),
        ("emergency_never_contain_record", "never_contain_snapshot"),
        ("directive_revocation_record", "emergency_never_contain"),
    ],
)
def test_ledger_record_type_unknown_or_wrong_rejected(
    fixture_name: str,
    wrong_record_type: str,
    request: pytest.FixtureRequest,
) -> None:
    """Unrecognized or mismatched record_type must fail validation (docs/spec chain integrity)."""
    model = request.getfixturevalue(fixture_name)
    data = model.model_dump(mode="json")
    data["record_type"] = wrong_record_type
    model_type = type(model)
    with pytest.raises(ValidationError):
        model_type.model_validate(data)


def test_ledger_record_types_are_distinct() -> None:
    from praetor.contracts.edict import DecisionEdict
    from praetor.contracts.ledger import (
        DirectiveRevocationRecord,
        EmergencyNeverContainRecord,
        NeverContainSnapshotRecord,
    )

    record_types = {
        DecisionEdict.model_fields["record_type"].default,
        DirectiveRevocationRecord.model_fields["record_type"].default,
        NeverContainSnapshotRecord.model_fields["record_type"].default,
        EmergencyNeverContainRecord.model_fields["record_type"].default,
    }
    assert len(record_types) == 4
    assert record_types == {
        "decision_edict",
        "directive_revocation",
        "never_contain_snapshot",
        "emergency_never_contain",
    }
