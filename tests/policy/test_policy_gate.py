"""TASK-017 deterministic PolicyGate tests."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from tests.policy.conftest import (
    NOW,
    account_bundle,
    auto_contain_judgment,
    host_bundle,
    persist_snapshot_with_overrides,
)

from praetor.config.emergency import add_emergency_never_contain
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.contracts.org_config_sections import ContainmentPolicy, ContainmentRule
from praetor.hashing import derive_idempotency_key
from praetor.ledger.store import fetch_ledger_rows
from praetor.policy.containment_policy import (
    NEVER_CONTAIN_LIVE_CONFLICT,
    NEVER_CONTAIN_SNAPSHOT,
    POLICY_AMBIGUITY,
)
from praetor.policy.gate import (
    CONTAINMENT_BREAKER_OPEN,
    INVALID_MODEL_CITATION,
    LATENCY_SLA_EXCEEDED,
    PROVIDER_HEALTH_BREAKER_OPEN,
    QUEUE_AGING_EXCEEDED,
    RATE_LIMIT_EXCEEDED,
    REVOCATION_FEED_UNHEALTHY,
    evaluate_policy_gate,
    evaluation_to_policy_gate_result,
)
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    AMBIGUOUS_TARGET_IDENTITY,
)
from praetor.policy.state import (
    BreakerDomain,
    init_policy_state_schema,
    rate_limit_scope_key,
    set_breaker_open,
    set_rate_counter,
)
from praetor.revocation.outbox import (
    init_revocation_feed_export_schema,
    set_feed_unhealthy,
)
from praetor.runtime.singleton import SingletonLock
from praetor.runtime.startup import open_production_state_store
from praetor.state.sqlite_guard import StartupGuardError


def _gate(
    activated,
    org_snapshot,
    *,
    bundle=None,
    judgment=None,
    alert_identity: str = "ALERT-POLICY-001",
    decision_id: str = "dec-test-001",
    **kwargs,
):
    bundle = bundle or host_bundle()
    judgment = judgment or auto_contain_judgment(bundle)
    return evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity=alert_identity,
        decision_id=decision_id,
        now=NOW,
        **kwargs,
    )


def test_invalid_citation_escalates(activated, org_snapshot) -> None:
    bundle = host_bundle()
    judgment = auto_contain_judgment(
        bundle,
        refs=[CitedEvidenceRef(evidence_id="missing", field_path="host_id")],
    )
    result = _gate(activated, org_snapshot, bundle=bundle, judgment=judgment)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [INVALID_MODEL_CITATION]
    assert result.system_fault_escalation is True


def test_snapshot_never_contain_escalates(activated, org_snapshot) -> None:
    bundle = host_bundle(host_id="dc-01")
    result = _gate(activated, org_snapshot, bundle=bundle)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [NEVER_CONTAIN_SNAPSHOT]
    assert result.system_fault_escalation is False


def test_live_emergency_never_contain_escalates(
    activated, org_snapshot, verifier
) -> None:
    add_emergency_never_contain(
        activated,
        token="soc-lead-token",
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "ws-01"},
        lifetime_seconds=3600,
        audit_reason="maintenance",
    )
    result = _gate(activated, org_snapshot)
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [NEVER_CONTAIN_LIVE_CONFLICT]
    assert result.system_fault_escalation is False


def test_emergency_entry_embedded_in_directive(
    activated, org_snapshot, verifier
) -> None:
    add_emergency_never_contain(
        activated,
        token="soc-lead-token",
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "other-host"},
        lifetime_seconds=3600,
        audit_reason="hold",
    )
    bundle = host_bundle(host_id="ws-02")
    result = _gate(activated, org_snapshot, bundle=bundle, alert_identity="ALERT-EMBED")
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert any(
        entry.get("source") == "emergency"
        for entry in result.live_never_contain_entries
    )


def test_insufficient_account_corroboration_escalates(activated, org_snapshot) -> None:
    bundle = account_bundle()
    bundle = bundle.model_copy(
        update={
            "facts": [bundle.facts[0]],
        }
    )
    result = _gate(
        activated, org_snapshot, bundle=bundle, alert_identity="ALERT-ACCT-BAD"
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [AMBIGUOUS_TARGET_IDENTITY]
    assert result.system_fault_escalation is False


def test_sid_without_corroboration_escalates_without_host_fallback(
    activated, org_snapshot
) -> None:
    """SID present but under-corroborated must not fall back to host containment."""
    from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
    from praetor.contracts.judgment import CitedEvidenceRef

    bundle = EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="ev-mixed",
                normalized_fields={
                    "host_id": "ws-01",
                    "target_sid": "S-1-5-21-1234567890-123456789-123456789-1001",
                },
                source_event_reference="sysmon:1",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=NOW,
            )
        ]
    )
    judgment = auto_contain_judgment(
        bundle,
        refs=[CitedEvidenceRef(evidence_id="ev-mixed", field_path="host_id")],
    )
    result = _gate(
        activated,
        org_snapshot,
        bundle=bundle,
        judgment=judgment,
        alert_identity="ALERT-SID-NO-CORR",
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [AMBIGUOUS_TARGET_IDENTITY]
    assert result.system_fault_escalation is False


def test_account_containment_disabled_when_gate_false(activated, org_snapshot) -> None:
    result = _gate(
        activated,
        org_snapshot,
        bundle=account_bundle(),
        alert_identity="ALERT-ACCT-OFF",
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [ACCOUNT_CONTAINMENT_DISABLED]


def test_account_auto_contain_when_feature_gate_enabled(
    activated, org_snapshot
) -> None:
    enabled = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        account_auto_contain_enabled=True,
    )
    result = _gate(
        activated,
        enabled,
        bundle=account_bundle(),
        alert_identity="ALERT-ACCT-ON",
    )
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.containment_directive is not None
    assert result.containment_directive.target_type == TargetType.ACCOUNT


def test_policy_ambiguity_escalates(activated, org_snapshot) -> None:
    policy = ContainmentPolicy(
        rules=[
            ContainmentRule.model_validate(
                {
                    "name": "host_allow",
                    "action": "auto_contain",
                    "scope": {"target_type": "host", "target_id": "ws-01"},
                }
            ),
            ContainmentRule.model_validate(
                {
                    "name": "host_deny",
                    "action": "escalate",
                    "scope": {"target_type": "host", "target_id": "ws-01"},
                }
            ),
        ],
        precedence=None,
    )
    snapshot = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        containment_policy=policy,
    )
    result = _gate(activated, snapshot, alert_identity="ALERT-AMBIG")
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [POLICY_AMBIGUITY]
    assert result.system_fault_escalation is False


def test_rate_limit_exceeded_escalates(activated, org_snapshot) -> None:
    init_policy_state_schema(activated.conn)
    scope_key = rate_limit_scope_key("per_host", target_type="host", target_id="ws-01")
    set_rate_counter(activated.conn, scope_key, 1)
    activated.conn.commit()
    result = _gate(activated, org_snapshot, alert_identity="ALERT-RATE")
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [RATE_LIMIT_EXCEEDED]
    assert result.system_fault_escalation is False


def test_duplicate_idempotency_key_suppresses_emission(activated, org_snapshot) -> None:
    bundle = host_bundle(host_id="ws-03")
    first = _gate(activated, org_snapshot, bundle=bundle, alert_identity="ALERT-DUP")
    assert first.containment_directive is not None
    assert first.directive_suppressed is False

    second = _gate(
        activated,
        org_snapshot,
        bundle=bundle,
        alert_identity="ALERT-DUP",
        decision_id="dec-dup-2",
    )
    assert second.final_disposition == Disposition.AUTO_CONTAIN
    assert second.directive_suppressed is True
    assert second.containment_directive is not None
    first_id = first.containment_directive.directive_id
    assert second.containment_directive.directive_id == first_id


def test_expired_directive_allows_fresh_reissue(activated, org_snapshot) -> None:
    issued = NOW - timedelta(minutes=10)
    idem_key = derive_idempotency_key("ALERT-SUPER", "host", "ws-04", "host-isolation")
    expired = ContainmentDirective(
        directive_id="dir-expired",
        decision_id="dec-old",
        target_type=TargetType.HOST,
        target_id="ws-04",
        scope="host-isolation",
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=30),
        idempotency_key=idem_key,
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    bundle = host_bundle(host_id="ws-04")
    activated.register_idempotency_key(
        idempotency_key=expired.idempotency_key,
        alert_identity="ALERT-SUPER",
        target_type="host",
        target_id="ws-04",
        scope="host-isolation",
    )
    activated.conn.execute(
        """
        INSERT INTO outstanding_containment_directives (
            directive_id, directive_json, issued_at, expires_at,
            target_type, target_id, revoked
        ) VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (
            expired.directive_id,
            expired.model_dump_json(),
            expired.issued_at.isoformat(),
            expired.expires_at.isoformat(),
            expired.target_type.value,
            expired.target_id,
        ),
    )
    activated.conn.commit()

    result = _gate(
        activated,
        org_snapshot,
        bundle=bundle,
        alert_identity="ALERT-SUPER",
        decision_id="dec-new",
    )
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.containment_directive is not None
    assert result.containment_directive.directive_id != expired.directive_id
    assert result.containment_directive.supersedes_directive_id is None
    assert result.containment_directive.idempotency_key == idem_key
    revocations = [
        row
        for row in fetch_ledger_rows(activated.conn)
        if row.record_type == "directive_revocation"
    ]
    assert revocations == []


def test_feed_unhealthy_blocks_auto_contain(activated, org_snapshot) -> None:
    init_revocation_feed_export_schema(activated.conn)
    set_feed_unhealthy(activated.conn, unhealthy=True)
    activated.conn.commit()
    result = _gate(activated, org_snapshot, alert_identity="ALERT-FEED")
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [REVOCATION_FEED_UNHEALTHY]
    assert result.system_fault_escalation is True


def test_proposed_and_final_dispositions_recorded_separately(
    activated, org_snapshot
) -> None:
    result = _gate(activated, org_snapshot, alert_identity="ALERT-RECORD")
    gate_result = evaluation_to_policy_gate_result(result)
    assert gate_result.proposed_disposition == Disposition.AUTO_CONTAIN
    assert gate_result.final_disposition == Disposition.AUTO_CONTAIN


def test_auto_contain_blocked_when_containment_breaker_open(
    activated, org_snapshot
) -> None:
    init_policy_state_schema(activated.conn)
    set_breaker_open(activated.conn, BreakerDomain.CONTAINMENT, open_=True)
    activated.conn.commit()
    result = _gate(activated, org_snapshot, alert_identity="ALERT-BREAKER")
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [CONTAINMENT_BREAKER_OPEN]
    assert result.system_fault_escalation is False


@pytest.mark.parametrize(
    ("kwarg", "fault_flag"),
    [
        ("latency_sla_exceeded", LATENCY_SLA_EXCEEDED),
        ("queue_aging_exceeded", QUEUE_AGING_EXCEEDED),
        ("provider_health_breaker_open", PROVIDER_HEALTH_BREAKER_OPEN),
    ],
)
def test_infrastructure_fault_escalates_with_system_fault(
    activated,
    org_snapshot,
    kwarg: str,
    fault_flag: str,
) -> None:
    result = _gate(
        activated,
        org_snapshot,
        alert_identity=f"ALERT-{fault_flag}",
        **{kwarg: True},
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [fault_flag]
    assert result.system_fault_escalation is True


def test_auto_contain_mutations_occur_in_one_transaction(
    activated, org_snapshot
) -> None:
    from praetor.policy.state import rate_limit_scope_key, read_rate_counter
    from praetor.state.idempotency import fetch_active_idempotency_key

    result = _gate(activated, org_snapshot, alert_identity="ALERT-TX")
    assert result.final_disposition == Disposition.AUTO_CONTAIN
    assert result.containment_directive is not None
    key = result.containment_directive.idempotency_key
    assert fetch_active_idempotency_key(activated.conn, key) is not None
    scope_key = rate_limit_scope_key("per_host", target_type="host", target_id="ws-01")
    assert read_rate_counter(activated.conn, scope_key) == 1


def test_production_entrypoint_requires_held_singleton(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    lock = SingletonLock(tmp_path)
    with pytest.raises(StartupGuardError, match="held singleton"):
        open_production_state_store(db, singleton=lock)


def test_production_entrypoint_opens_with_held_singleton(tmp_path: Path) -> None:
    from praetor.state.sqlite_guard import init_state_dir

    db = tmp_path / "state.db"
    init_state_dir(db)
    with SingletonLock(tmp_path) as lock:
        store = open_production_state_store(db, singleton=lock)
        store.close()
