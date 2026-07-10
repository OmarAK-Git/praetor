"""PolicyGate containment authorization boundary integration (V2-025 / PE-0014)."""

from __future__ import annotations

from tests.policy.conftest import (
    NOW,
    account_bundle,
    auto_contain_default_policy,
    auto_contain_judgment,
    host_bundle,
    persist_snapshot_with_overrides,
)

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.evidence.citations import ResolvedEvidenceCitation
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    meets_host_cited_corroboration,
)
from praetor.policy.containment_policy import extract_account_identity
from praetor.policy.gate import evaluate_policy_gate
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    INSUFFICIENT_CORROBORATION,
    evaluate_account_containment_eligibility,
)


def test_direct_eligibility_signals_auto_contain_without_feature_gate() -> None:
    """PE-0014: eligibility helper does not apply account_containment_disabled."""
    bundle = account_bundle()
    identity = extract_account_identity(list(bundle.facts))
    assert identity is not None

    result = evaluate_account_containment_eligibility(identity, bundle.facts)

    assert result.authorized is True
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.fault_flag is None


def test_policy_gate_blocks_bypass_of_account_containment_disabled(
    activated, org_snapshot
) -> None:
    bundle = account_bundle()
    identity = extract_account_identity(list(bundle.facts))
    assert identity is not None

    eligibility = evaluate_account_containment_eligibility(identity, bundle.facts)
    assert eligibility.authorized is True

    gate_result = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(bundle),
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity="ALERT-BOUNDARY-OFF",
        decision_id="dec-boundary-off",
        now=NOW,
    )

    assert gate_result.final_disposition == Disposition.ESCALATE
    assert gate_result.fault_flags == [ACCOUNT_CONTAINMENT_DISABLED]
    assert gate_result.containment_directive is None


def test_policy_gate_authorizes_when_feature_gate_enabled(
    activated, org_snapshot
) -> None:
    bundle = account_bundle()
    enabled = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        account_auto_contain_enabled=True,
        containment_policy=auto_contain_default_policy(),
    )

    gate_result = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(bundle),
        evidence_bundle=bundle,
        org_snapshot=enabled,
        alert_identity="ALERT-BOUNDARY-ON",
        decision_id="dec-boundary-on",
        now=NOW,
    )

    assert gate_result.final_disposition == Disposition.AUTO_CONTAIN
    assert gate_result.fault_flags == []
    assert gate_result.containment_directive is not None


def test_host_corroboration_helper_alone_does_not_authorize_containment(
    activated, org_snapshot
) -> None:
    bundle = host_bundle()
    sysmon = bundle.facts[0]
    security = bundle.facts[1]
    cited = (
        ResolvedEvidenceCitation(
            evidence_id=sysmon.evidence_id,
            field_path="host_id",
            value="ws-01",
            ambiguity_flag=False,
            provenance_path=SYSMON_EVENT_LOG,
        ),
        ResolvedEvidenceCitation(
            evidence_id=security.evidence_id,
            field_path="host_id",
            value="ws-01",
            ambiguity_flag=False,
            provenance_path=WINDOWS_SECURITY_LOG,
        ),
    )
    facts_by_id = {fact.evidence_id: fact for fact in bundle.facts}

    assert meets_host_cited_corroboration(
        cited,
        target_host_id="ws-01",
        facts_by_id=facts_by_id,
    )

    gate_result = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(
            bundle,
            refs=[
                CitedEvidenceRef(
                    evidence_id=sysmon.evidence_id,
                    field_path="process_name",
                )
            ],
        ),
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity="ALERT-HOST-BYPASS",
        decision_id="dec-host-bypass",
        now=NOW,
    )

    assert gate_result.final_disposition == Disposition.ESCALATE
    assert gate_result.fault_flags == [INSUFFICIENT_CORROBORATION]
    assert gate_result.containment_directive is None
