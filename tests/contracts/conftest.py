"""Minimal valid contract fixtures for round-trip tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from praetor.contracts.alert import AlertEnvelope
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.governance import AnalystAnnotation
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
    RevocationReason,
)
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.policy import PolicyGateResult

UTC = timezone.utc
NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def _section() -> dict:
    return {}


@pytest.fixture
def alert_envelope() -> AlertEnvelope:
    return AlertEnvelope(alert_identity="ALERT-001")


@pytest.fixture
def evidence_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="ev-1",
                normalized_fields={"process_name": "cmd.exe"},
                source_event_reference="sysmon:1:100",
                raw_source='{"EventID":1}',
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=NOW,
            )
        ]
    )


@pytest.fixture
def org_config_snapshot() -> OrgConfigSnapshot:
    return OrgConfigSnapshot(
        snapshot_hash="sha256:org:abc",
        version_metadata=_section(),
        known_principals=_section(),
        assets_and_asset_groups=_section(),
        normal_admin_patterns=_section(),
        containment_exclusions=_section(),
        business_context=_section(),
        containment_policy=_section(),
        directive_lifetime_policy=_section(),
        emergency_never_contain_policy=_section(),
        rate_limit_policy=_section(),
        provider_health_circuit_breaker_policy=_section(),
        containment_circuit_breaker_policy=_section(),
        revocation_feed_policy=_section(),
        consumer_clock_skew_policy=_section(),
        latency_and_queue_aging_policy=_section(),
        provisional_alert_rate_targets=_section(),
    )


@pytest.fixture
def model_judgment() -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[CitedEvidenceRef(evidence_id="ev-1", field_path="process_name")],
        key_tells=["suspicious parent"],
        org_config_refs=["containment_policy.default"],
        benign_alternatives=["admin tooling"],
        benign_alternatives_ruled_out=["none"],
        convergence_reasoning="multiple signals",
        narrative="summary",
        model_name="fake",
        provider_name="fake",
    )


@pytest.fixture
def policy_gate_result() -> PolicyGateResult:
    return PolicyGateResult(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        final_disposition=Disposition.STANDARD_REVIEW,
    )


@pytest.fixture
def containment_directive() -> ContainmentDirective:
    issued = NOW
    return ContainmentDirective(
        directive_id="dir-1",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="host-01",
        scope="host-isolation",
        evidence_refs=["ev-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-1",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.PROPOSED,
        live_never_contain_hash="sha256:nc:abc",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )


@pytest.fixture
def decision_edict(
    model_judgment: ModelJudgment,
    policy_gate_result: PolicyGateResult,
) -> DecisionEdict:
    return DecisionEdict(
        decision_id="dec-1",
        alert_reference="ALERT-001",
        evidence_bundle_hash="sha256:bundle:abc",
        org_config_snapshot_hash="sha256:org:abc",
        live_never_contain_hash="sha256:nc:abc",
        model_judgment=model_judgment,
        policy_gate_result=policy_gate_result,
        final_disposition=Disposition.STANDARD_REVIEW,
        system_fault_escalation=False,
        fault_flags=[],
        stamp_status="succeeded",
        timing_metadata={},
        ledger_previous_hash="sha256:ledger:prev",
        ledger_current_hash="sha256:ledger:curr",
        ticket_stamp_payload={},
        decided_at=NOW,
    )


@pytest.fixture
def never_contain_snapshot_record() -> NeverContainSnapshotRecord:
    return NeverContainSnapshotRecord(
        snapshot_id="snap-1",
        snapshot_hash="sha256:snap:abc",
        snapshot_content=[],
        evaluated_at=NOW,
        triggered_by_decision_id="dec-1",
    )


@pytest.fixture
def emergency_never_contain_record() -> EmergencyNeverContainRecord:
    added = NOW
    return EmergencyNeverContainRecord(
        entry_id="enc-1",
        target_specification={"host": "host-01"},
        added_by="soc-lead-1",
        added_at=added,
        expires_at=added + timedelta(hours=1),
        audit_reason="maintenance",
    )


@pytest.fixture
def directive_revocation_record() -> DirectiveRevocationRecord:
    return DirectiveRevocationRecord(
        revocation_id="rev-1",
        directive_id="dir-1",
        reason=RevocationReason.MANUAL,
        reason_code="manual_revocation",
        triggered_by="soc-lead-1",
        revoked_at=NOW,
        ledger_commit_at=NOW,
        idempotency_key_cleared=True,
    )


@pytest.fixture
def revocation_feed_record() -> RevocationFeedRecord:
    return RevocationFeedRecord(
        sequence_number=1,
        directive_id="dir-1",
        revocation_id="rev-1",
        reason_code="manual_revocation",
        revoked_at=NOW,
        ledger_commit_at=NOW,
        record_checksum="sha256:feed:chk",
    )


@pytest.fixture
def system_health_alert() -> SystemHealthAlert:
    return SystemHealthAlert(alert_code="revocation_feed_unhealthy", emitted_at=NOW)


@pytest.fixture
def analyst_annotation() -> AnalystAnnotation:
    return AnalystAnnotation(
        disposition_correct=True,
        corrected_disposition=None,
        comment="looks right",
        reviewer_identity="analyst-1",
        timestamp=NOW,
    )


@pytest.fixture
def canonical_account_identity() -> CanonicalAccountIdentity:
    return CanonicalAccountIdentity(
        sid="S-1-5-21-1234567890-123456789-123456789-1001",
        domain="CORP",
        account_name="jdoe",
        account_type="user",
        authority_source="windows_security_log",
        ambiguity_flag=False,
    )
