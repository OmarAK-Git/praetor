"""PolicyGate host corroboration floor integration (V2-011)."""

from __future__ import annotations

from datetime import UTC, datetime

from tests.policy.conftest import (
    NOW,
    account_bundle,
    auto_contain_judgment,
    host_bundle,
    permissive_org_snapshot,
)

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.evidence.provenance import SYSMON_EVENT_LOG
from praetor.policy.gate import evaluate_policy_gate
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    INSUFFICIENT_CORROBORATION,
)


def _gate(activated, org_snapshot, *, bundle, judgment, **kwargs):
    snapshot = permissive_org_snapshot(activated, org_snapshot)
    return evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=snapshot,
        alert_identity="ALERT-HOST-CORROB",
        decision_id="dec-host-corrob",
        now=NOW,
        **kwargs,
    )


def test_host_single_cited_provenance_escalates(activated, org_snapshot) -> None:
    bundle = host_bundle()
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(
                evidence_id="ev-host-sysmon",
                field_path="process_name",
            )
        ],
    )
    result = _gate(activated, org_snapshot, bundle=bundle, judgment=judgment)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [INSUFFICIENT_CORROBORATION]
    assert result.system_fault_escalation is False


def test_host_sysmon_security_citations_auto_contain(activated, org_snapshot) -> None:
    bundle = host_bundle(host_id="ws-corrob-ok")
    judgment = auto_contain_judgment(bundle)
    result = _gate(activated, org_snapshot, bundle=bundle, judgment=judgment)
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.fault_flags == []
    assert result.containment_directive is not None
    assert result.containment_directive.target_id == "ws-corrob-ok"


def test_sole_ambiguous_cited_fact_escalates(activated, org_snapshot) -> None:
    ts = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    bundle = EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="host-ambiguous-only",
                normalized_fields={"host_id": "WS-AMB", "process_name": "cmd.exe"},
                source_event_reference="syn:amb:1",
                raw_source="{}",
                provenance_path=SYSMON_EVENT_LOG,
                ambiguity_flag=True,
                timestamp=ts,
            ),
        ]
    )
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(
                evidence_id="host-ambiguous-only",
                field_path="host_id",
            )
        ],
    )
    result = _gate(activated, org_snapshot, bundle=bundle, judgment=judgment)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [INSUFFICIENT_CORROBORATION]


def test_two_sysmon_citations_same_path_escalates(activated, org_snapshot) -> None:
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
                provenance_path=SYSMON_EVENT_LOG,
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
                provenance_path=SYSMON_EVENT_LOG,
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
    result = _gate(activated, org_snapshot, bundle=bundle, judgment=judgment)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [INSUFFICIENT_CORROBORATION]


def test_unrelated_security_cite_does_not_corroborate_host_target(
    activated, org_snapshot
) -> None:
    ts = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    bundle = EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="host-sysmon",
                normalized_fields={"host_id": "ws-01", "process_name": "cmd.exe"},
                source_event_reference="syn:sysmon:1",
                raw_source="{}",
                provenance_path=SYSMON_EVENT_LOG,
                ambiguity_flag=False,
                timestamp=ts,
            ),
            EvidenceFact(
                evidence_id="host-security",
                normalized_fields={"event_id": 4624},
                source_event_reference="syn:security:1",
                raw_source="{}",
                provenance_path="windows_security_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
        ]
    )
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(evidence_id="host-sysmon", field_path="host_id"),
            CitedEvidenceRef(evidence_id="host-security", field_path="event_id"),
        ],
    )
    result = _gate(activated, org_snapshot, bundle=bundle, judgment=judgment)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [INSUFFICIENT_CORROBORATION]


def test_account_path_unaffected_by_host_corroboration_flag(
    activated, org_snapshot
) -> None:
    bundle = account_bundle()
    judgment = auto_contain_judgment(bundle)
    result = evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity="ALERT-ACCOUNT-CORROB",
        decision_id="dec-account-corrob",
        now=NOW,
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [ACCOUNT_CONTAINMENT_DISABLED]
    assert INSUFFICIENT_CORROBORATION not in result.fault_flags
