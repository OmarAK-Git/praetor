"""TASK-017 ContainmentDirective embedded-hash compliance (contracts.md §9)."""

from __future__ import annotations

from tests.policy.conftest import NOW, host_bundle

from praetor.hashing import compute_never_contain_entries_hash
from praetor.policy.containment_policy import ContainmentTarget
from praetor.policy.directive_builder import build_containment_directive_in_transaction
from praetor.policy.gate import evaluate_policy_gate
from praetor.state.sqlite_guard import critical_transaction


def test_directive_embedded_hash_matches_via_gate(activated, org_snapshot) -> None:
    bundle = host_bundle(host_id="ws-01")
    from tests.policy.conftest import auto_contain_judgment

    result = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(bundle),
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity="ALERT-HASH-GATE",
        decision_id="dec-hash-gate",
        now=NOW,
    )
    assert result.containment_directive is not None
    directive = result.containment_directive
    assert (
        compute_never_contain_entries_hash(directive.embedded_never_contain_entries)
        == directive.live_never_contain_hash
    )


def test_directive_embedded_hash_includes_same_target_emergency_subset(
    activated, org_snapshot
) -> None:
    """Builder hashes the target-relevant subset, including same-target emergencies."""
    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    live_entries: list[dict[str, object]] = [
        {
            "target_type": "host",
            "target_id": "ws-01",
            "source": "emergency",
        },
        {
            "target_type": "host",
            "target_id": "dc-01",
        },
    ]
    with critical_transaction(activated.conn):
        directive = build_containment_directive_in_transaction(
            activated.conn,
            decision_id="dec-hash-emergency",
            alert_identity="ALERT-HASH-EM",
            target=target,
            evidence_refs=["ev-host-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=live_entries,
            now=NOW,
        )
    assert len(directive.embedded_never_contain_entries) == 1
    assert directive.embedded_never_contain_entries[0].get("source") == "emergency"
    assert (
        compute_never_contain_entries_hash(directive.embedded_never_contain_entries)
        == directive.live_never_contain_hash
    )
