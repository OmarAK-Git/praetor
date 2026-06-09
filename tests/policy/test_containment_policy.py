"""TASK-017 containment policy unit tests."""

from __future__ import annotations

from tests.policy.conftest import account_bundle, host_bundle

from praetor.contracts.org_config_sections import ContainmentPolicy, ContainmentRule
from praetor.policy.containment_policy import (
    POLICY_AMBIGUITY,
    PolicyAction,
    evaluate_target_containment_policy,
    resolve_containment_target,
    target_blocked_by_snapshot,
)


def test_resolve_host_target_from_evidence() -> None:
    target = resolve_containment_target(host_bundle())
    assert target is not None
    assert target.target_type == "host"
    assert target.target_id == "ws-01"


def test_resolve_account_target_requires_corroboration() -> None:
    target = resolve_containment_target(account_bundle())
    assert target is not None
    assert target.target_type == "account"
    assert target.target_id.startswith("S-1-5-")


def test_snapshot_never_contain_blocks_target(org_snapshot) -> None:
    target = resolve_containment_target(host_bundle(host_id="dc-01"))
    assert target is not None
    assert target_blocked_by_snapshot(org_snapshot, target)


def test_target_scoped_policy_conflict_is_ambiguous(org_snapshot) -> None:
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
    snapshot = org_snapshot.model_copy(update={"containment_policy": policy})
    target = resolve_containment_target(host_bundle(host_id="ws-01"))
    assert target is not None
    evaluation = evaluate_target_containment_policy(snapshot, target)
    assert evaluation.action == PolicyAction.AMBIGUOUS
    assert evaluation.fault_flag == POLICY_AMBIGUITY
