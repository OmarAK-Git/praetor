"""Citation-anchored host containment targeting (DEC-052 / Option A)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from evals.correlation_gate import REPO_ROOT, load_correlation_expected
from evals.run_phase3_gate import (
    INCIDENT_HOST_ID,
    NOISE_HOST_ID,
    REQUIRED_EXPECTED_PATH,
)
from tests.policy.conftest import NOW, auto_contain_judgment, permissive_org_snapshot

from praetor.contracts.containment import TargetType
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.policy.containment_policy import (
    ContainmentTargetResolution,
    resolve_containment_target,
    resolve_host_target_from_citations,
)
from praetor.policy.gate import evaluate_policy_gate
from praetor.policy.identity import AMBIGUOUS_CONTAINMENT_TARGET


def _two_host_bundle() -> EvidenceBundle:
    ts = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="host-a-1",
                normalized_fields={
                    "host_id": "WORKSTATION1",
                    "process_name": "cmd.exe",
                },
                source_event_reference="syn:a:1",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
            EvidenceFact(
                evidence_id="host-b-1",
                normalized_fields={
                    "host_id": "WORKSTATION2",
                    "process_name": "notepad.exe",
                },
                source_event_reference="syn:b:1",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
        ]
    )


def _sysmon_only_noisy_bundle() -> EvidenceBundle:
    scenario = load_correlation_expected(REQUIRED_EXPECTED_PATH)
    inputs = scenario.inputs
    anchor_time = datetime.fromisoformat(
        str(inputs.get("anchor_time")).replace("Z", "+00:00")
    )
    window_seconds = int(inputs.get("window_seconds", 300))
    sysmon_events: list[dict] = []
    for path_value in inputs.get("sysmon_fixtures") or []:
        fixture_path = REPO_ROOT / str(path_value)
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        sysmon_events.extend(load_fixture_events(payload))
    return correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=[],
        anchor_time=anchor_time,
        window_seconds=window_seconds,
    ).bundle


def test_resolve_host_target_from_citations_single_host() -> None:
    bundle = _two_host_bundle()
    resolution = resolve_host_target_from_citations(
        bundle,
        frozenset({"host-a-1"}),
    )
    assert resolution == ContainmentTargetResolution(
        target=resolution.target,
        ambiguous=False,
    )
    assert resolution.target is not None
    assert resolution.target.target_id == "WORKSTATION1"


def test_resolve_host_target_from_citations_multi_host_is_ambiguous() -> None:
    bundle = _two_host_bundle()
    resolution = resolve_host_target_from_citations(
        bundle,
        frozenset({"host-a-1", "host-b-1"}),
    )
    assert resolution.ambiguous is True
    assert resolution.target is None


def test_uncited_cross_host_noise_does_not_capture_target(
    activated,
    org_snapshot,
) -> None:
    bundle = _sysmon_only_noisy_bundle()
    incident_fact = next(
        fact
        for fact in bundle.facts
        if fact.normalized_fields.get("host_id") == INCIDENT_HOST_ID
    )
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(
                evidence_id=incident_fact.evidence_id,
                field_path="host_id",
            )
        ],
    )

    snapshot = permissive_org_snapshot(activated, org_snapshot)
    result = evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=snapshot,
        alert_identity="ALERT-CITATION-NOISE",
        decision_id="dec-citation-noise",
        now=NOW,
    )

    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.containment_directive is not None
    assert result.containment_directive.target_type == TargetType.HOST
    assert result.containment_directive.target_id == INCIDENT_HOST_ID
    assert result.containment_directive.target_id != NOISE_HOST_ID


def test_multi_cited_hosts_escalates_ambiguous_containment_target(
    activated,
    org_snapshot,
) -> None:
    bundle = _two_host_bundle()
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(evidence_id="host-a-1", field_path="host_id"),
            CitedEvidenceRef(evidence_id="host-b-1", field_path="host_id"),
        ],
    )

    result = evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity="ALERT-MULTI-HOST",
        decision_id="dec-multi-host",
        now=NOW,
    )

    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [AMBIGUOUS_CONTAINMENT_TARGET]
    assert result.system_fault_escalation is False


def test_single_host_multi_citation_auto_contain(activated, org_snapshot) -> None:
    ts = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    bundle = EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="host-a-1",
                normalized_fields={
                    "host_id": "WORKSTATION1",
                    "process_name": "cmd.exe",
                },
                source_event_reference="syn:a:1",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
            EvidenceFact(
                evidence_id="host-a-2",
                normalized_fields={
                    "host_id": "WORKSTATION1",
                    "process_name": "powershell.exe",
                },
                source_event_reference="syn:a:2",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
        ]
    )
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(evidence_id="host-a-1", field_path="host_id"),
            CitedEvidenceRef(evidence_id="host-a-2", field_path="process_name"),
        ],
    )

    resolution = resolve_containment_target(
        bundle,
        frozenset({"host-a-1", "host-a-2"}),
    )
    assert resolution.ambiguous is False
    assert resolution.target is not None
    assert resolution.target.target_id == "WORKSTATION1"

    snapshot = permissive_org_snapshot(activated, org_snapshot)
    result = evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=snapshot,
        alert_identity="ALERT-SINGLE-HOST-MULTI-CITE",
        decision_id="dec-single-host-multi-cite",
        now=NOW,
    )

    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.containment_directive is not None
    assert result.containment_directive.target_id == "WORKSTATION1"
