"""TASK-029: correlator identity compliance on real fixture shapes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tests.policy.conftest import (
    NOW,
    auto_contain_judgment,
    persist_snapshot_with_overrides,
)

from praetor.contracts.containment import TargetType
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.correlation.security_log import normalize_security_event
from praetor.correlation.sysmon import normalize_sysmon_event
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    meets_account_corroboration,
)
from praetor.policy.containment_policy import (
    extract_account_identity,
    resolve_host_target,
)
from praetor.policy.gate import PolicyGateEvaluation, evaluate_policy_gate
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    AMBIGUOUS_TARGET_IDENTITY,
    evaluate_account_containment_eligibility,
)
from praetor.state.store import StateStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SYSMON_FIXTURES = FIXTURES / "sysmon"
SECURITY_FIXTURES = FIXTURES / "security"
SYNTHETIC_FIXTURES = FIXTURES / "synthetic"
ANCHOR = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


def _load_json_fixture(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_fixture_events(payload)


def _correlate(
    *,
    sysmon_events: list[dict],
    security_events: list[dict] | None = None,
) -> EvidenceBundle:
    result = correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=security_events or [],
        anchor_time=ANCHOR,
    )
    return result.bundle


def _full_correlated_bundle() -> EvidenceBundle:
    return _correlate(
        sysmon_events=_load_json_fixture(SYSMON_FIXTURES / "process_chain.json"),
        security_events=_load_json_fixture(
            SECURITY_FIXTURES / "successful_logon_4624.json"
        ),
    )


def _load_synthetic(
    name: str,
) -> tuple[CanonicalAccountIdentity | None, list[EvidenceFact]]:
    payload = json.loads((SYNTHETIC_FIXTURES / name).read_text(encoding="utf-8"))
    identity = (
        CanonicalAccountIdentity.model_validate(payload["identity"])
        if "identity" in payload
        else None
    )
    facts = EvidenceBundle.model_validate({"facts": payload["facts"]}).facts
    return identity, facts


def _judgment_for_bundle(bundle: EvidenceBundle) -> CitedEvidenceRef:
    """Pick a citable field from the first fact for AUTO_CONTAIN citations."""
    fact = bundle.facts[0]
    if "host_id" in fact.normalized_fields:
        return CitedEvidenceRef(
            evidence_id=fact.evidence_id,
            field_path="host_id",
        )
    return CitedEvidenceRef(
        evidence_id=fact.evidence_id,
        field_path="process_name",
    )


def _run_policy_gate(
    activated: StateStore,
    org_snapshot,
    bundle: EvidenceBundle,
    *,
    alert_identity: str,
    extra_refs: list[CitedEvidenceRef] | None = None,
) -> PolicyGateEvaluation:
    refs = extra_refs or [_judgment_for_bundle(bundle)]
    judgment = auto_contain_judgment(bundle, refs=refs)
    return evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity=alert_identity,
        decision_id=f"dec-{alert_identity.lower()}",
        now=NOW,
    )


def test_real_sysmon_process_creation_provenance_path() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    fact = normalize_sysmon_event(events[0])

    assert fact.provenance_path == SYSMON_EVENT_LOG
    assert fact.normalized_fields["process_name"] == "cmd.exe"


def test_real_security_logon_provenance_path() -> None:
    events = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")
    fact = normalize_security_event(events[0])

    assert fact.provenance_path == WINDOWS_SECURITY_LOG
    assert fact.normalized_fields["target_sid"].startswith("S-1-5-21-")


def test_correlated_real_pair_satisfies_corroboration() -> None:
    bundle = _full_correlated_bundle()

    paths = {fact.provenance_path for fact in bundle.facts}
    assert SYSMON_EVENT_LOG in paths
    assert WINDOWS_SECURITY_LOG in paths
    assert meets_account_corroboration(bundle.facts) is True


def test_correlated_real_pair_authorizes_containment() -> None:
    bundle = _full_correlated_bundle()
    identity = extract_account_identity(list(bundle.facts))

    assert identity is not None
    assert identity.sid.startswith("S-1-5-21-")

    result = evaluate_account_containment_eligibility(identity, bundle.facts)

    assert result.authorized is True
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.fault_flag is None


def test_two_sysmon_facts_reject_corroboration_and_host_contain_via_policy_gate(
    activated, org_snapshot
) -> None:
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    bundle = _correlate(sysmon_events=sysmon_events)

    sysmon_facts = [
        fact for fact in bundle.facts if fact.provenance_path == SYSMON_EVENT_LOG
    ]
    assert len(sysmon_facts) == 2
    assert meets_account_corroboration(bundle.facts) is False
    assert extract_account_identity(list(bundle.facts)) is None

    target = resolve_host_target(bundle)
    assert target is not None
    assert target.target_type == "host"
    assert target.target_id == "WORKSTATION1"

    result = _run_policy_gate(
        activated,
        org_snapshot,
        bundle,
        alert_identity="ALERT-2-SYSMON",
    )
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert AMBIGUOUS_TARGET_IDENTITY not in result.fault_flags
    assert result.containment_directive is not None
    assert result.containment_directive.target_type == TargetType.HOST
    assert result.containment_directive.target_id == "WORKSTATION1"


def test_ambiguous_sysmon_sets_ambiguity_flag() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json")
    fact = normalize_sysmon_event(events[0])

    assert fact.ambiguity_flag is True
    assert fact.provenance_path == SYSMON_EVENT_LOG
    assert fact.normalized_fields["user"] == "jdoe"


def test_ambiguous_sysmon_only_resolves_host_via_policy_gate(
    activated, org_snapshot
) -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json")
    bundle = _correlate(sysmon_events=events)

    assert len(bundle.facts) == 1
    assert bundle.facts[0].ambiguity_flag is True
    assert meets_account_corroboration(bundle.facts) is False
    assert extract_account_identity(list(bundle.facts)) is None

    target = resolve_host_target(bundle)
    assert target is not None
    assert target.target_type == "host"
    assert target.target_id == "WORKSTATION1"

    result = _run_policy_gate(
        activated,
        org_snapshot,
        bundle,
        alert_identity="ALERT-AMB-SYSMON",
    )
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert AMBIGUOUS_TARGET_IDENTITY not in result.fault_flags
    assert result.containment_directive is not None
    assert result.containment_directive.target_type == TargetType.HOST


def test_corroborated_ambiguous_identity_auto_contain_when_gate_enabled(
    activated, org_snapshot
) -> None:
    """spec.md:309 escalates only when ambiguity_flag and insufficient corroboration."""
    bundle = _correlate(
        sysmon_events=_load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json"),
        security_events=_load_json_fixture(
            SECURITY_FIXTURES / "successful_logon_4624.json"
        ),
    )
    identity = extract_account_identity(list(bundle.facts))

    assert identity is not None
    assert identity.ambiguity_flag is True
    assert meets_account_corroboration(bundle.facts) is True

    enabled = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        account_auto_contain_enabled=True,
    )
    security_fact = next(
        fact for fact in bundle.facts if fact.provenance_path == WINDOWS_SECURITY_LOG
    )
    result = _run_policy_gate(
        activated,
        enabled,
        bundle,
        alert_identity="ALERT-AMB-CORR",
        extra_refs=[
            CitedEvidenceRef(
                evidence_id=security_fact.evidence_id,
                field_path="target_sid",
            )
        ],
    )

    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert AMBIGUOUS_TARGET_IDENTITY not in result.fault_flags
    assert result.containment_directive is not None
    assert result.containment_directive.target_type == TargetType.ACCOUNT
    assert result.containment_directive.target_id == identity.sid


def test_real_correlated_bundle_account_containment_disabled(
    activated, org_snapshot
) -> None:
    bundle = _full_correlated_bundle()
    security_fact = next(
        fact for fact in bundle.facts if fact.provenance_path == WINDOWS_SECURITY_LOG
    )
    result = _run_policy_gate(
        activated,
        org_snapshot,
        bundle,
        alert_identity="ALERT-ACCT-GATE-OFF",
        extra_refs=[
            CitedEvidenceRef(
                evidence_id=security_fact.evidence_id,
                field_path="target_sid",
            )
        ],
    )

    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [ACCOUNT_CONTAINMENT_DISABLED]
    assert result.system_fault_escalation is False


def test_real_correlated_bundle_account_auto_contain_when_gate_enabled(
    activated, org_snapshot
) -> None:
    bundle = _full_correlated_bundle()
    identity = extract_account_identity(list(bundle.facts))
    assert identity is not None

    enabled = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        account_auto_contain_enabled=True,
    )
    security_fact = next(
        fact for fact in bundle.facts if fact.provenance_path == WINDOWS_SECURITY_LOG
    )
    result = _run_policy_gate(
        activated,
        enabled,
        bundle,
        alert_identity="ALERT-ACCT-GATE-ON",
        extra_refs=[
            CitedEvidenceRef(
                evidence_id=security_fact.evidence_id,
                field_path="target_sid",
            )
        ],
    )

    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.containment_directive is not None
    assert result.containment_directive.target_type == TargetType.ACCOUNT
    assert result.containment_directive.target_id == identity.sid


def test_real_eligible_pair_matches_synthetic_eligible() -> None:
    synthetic_identity, synthetic_facts = _load_synthetic("account_eligible_valid.json")
    assert synthetic_identity is not None
    synthetic_result = evaluate_account_containment_eligibility(
        synthetic_identity,
        synthetic_facts,
    )

    real_bundle = _full_correlated_bundle()
    real_identity = extract_account_identity(list(real_bundle.facts))
    assert real_identity is not None
    real_result = evaluate_account_containment_eligibility(
        real_identity,
        real_bundle.facts,
    )

    assert synthetic_result.authorized is True
    assert real_result.authorized == synthetic_result.authorized
    assert real_result.final_disposition == synthetic_result.final_disposition
    assert real_result.fault_flag == synthetic_result.fault_flag


def test_real_sysmon_only_matches_synthetic_same_provenance_rejection() -> None:
    _, synthetic_facts = _load_synthetic("account_same_provenance.json")
    assert meets_account_corroboration(synthetic_facts) is False

    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    real_bundle = _correlate(sysmon_events=sysmon_events)

    assert meets_account_corroboration(real_bundle.facts) is False
