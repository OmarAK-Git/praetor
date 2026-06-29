"""TASK-017 containment policy unit tests."""

from __future__ import annotations

from tests.policy.conftest import account_bundle, host_bundle

from praetor.contracts.org_config_sections import ContainmentPolicy, ContainmentRule
from praetor.policy.containment_policy import (
    CONTAINMENT_POLICY_DENIED,
    CONTAINMENT_POLICY_ESCALATION_REQUIRED,
    POLICY_AMBIGUITY,
    PolicyAction,
    evaluate_target_containment_policy,
    resolve_account_target,
    resolve_host_target,
    target_blocked_by_snapshot,
)


def test_resolve_host_target_from_evidence() -> None:
    target = resolve_host_target(host_bundle())
    assert target is not None
    assert target.target_type == "host"
    assert target.target_id == "ws-01"


def test_resolve_account_target_requires_corroboration() -> None:
    target = resolve_account_target(account_bundle())
    assert target is not None
    assert target.target_type == "account"
    assert target.target_id.startswith("S-1-5-")


def test_snapshot_never_contain_blocks_target(org_snapshot) -> None:
    target = resolve_host_target(host_bundle(host_id="dc-01"))
    assert target is not None
    assert target_blocked_by_snapshot(org_snapshot, target)


def test_catch_all_scope_matches_any_target(org_snapshot) -> None:
    policy = ContainmentPolicy(
        default_action="escalate",
        rules=[
            ContainmentRule(
                name="catch_all_deny",
                action="deny",
                scope={"catch_all": True},
            ),
        ],
    )
    snapshot = org_snapshot.model_copy(update={"containment_policy": policy})
    target = resolve_host_target(host_bundle(host_id="ws-99"))
    assert target is not None
    evaluation = evaluate_target_containment_policy(snapshot, target)
    assert evaluation.action == PolicyAction.DENY
    assert evaluation.fault_flag == CONTAINMENT_POLICY_DENIED


def test_sole_escalate_rule_blocks_containment(org_snapshot) -> None:
    policy = ContainmentPolicy(
        default_action="allow",
        rules=[
            ContainmentRule(
                name="default_escalate",
                action="escalate",
                scope={"catch_all": True},
            ),
        ],
    )
    snapshot = org_snapshot.model_copy(update={"containment_policy": policy})
    target = resolve_host_target(host_bundle(host_id="ws-01"))
    assert target is not None
    evaluation = evaluate_target_containment_policy(snapshot, target)
    assert evaluation.action == PolicyAction.ESCALATE
    assert evaluation.fault_flag == CONTAINMENT_POLICY_ESCALATION_REQUIRED


def test_deny_and_escalate_distinct_results(org_snapshot) -> None:
    deny_policy = ContainmentPolicy(
        default_action="escalate",
        rules=[
            ContainmentRule(
                name="host_deny",
                action="deny",
                scope={"target_type": "host", "target_id": "ws-01"},
            ),
        ],
    )
    escalate_policy = ContainmentPolicy(
        default_action="allow",
        rules=[
            ContainmentRule(
                name="host_escalate",
                action="escalate",
                scope={"target_type": "host", "target_id": "ws-01"},
            ),
        ],
    )
    target = resolve_host_target(host_bundle(host_id="ws-01"))
    assert target is not None
    deny_eval = evaluate_target_containment_policy(
        org_snapshot.model_copy(update={"containment_policy": deny_policy}),
        target,
    )
    escalate_eval = evaluate_target_containment_policy(
        org_snapshot.model_copy(update={"containment_policy": escalate_policy}),
        target,
    )
    assert deny_eval.action == PolicyAction.DENY
    assert escalate_eval.action == PolicyAction.ESCALATE
    assert deny_eval.fault_flag == CONTAINMENT_POLICY_DENIED
    assert escalate_eval.fault_flag == CONTAINMENT_POLICY_ESCALATION_REQUIRED
    assert deny_eval.fault_flag != escalate_eval.fault_flag


def test_target_scoped_policy_conflict_is_ambiguous(org_snapshot) -> None:
    policy = ContainmentPolicy(
        default_action="escalate",
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
    target = resolve_host_target(host_bundle(host_id="ws-01"))
    assert target is not None
    evaluation = evaluate_target_containment_policy(snapshot, target)
    assert evaluation.action == PolicyAction.AMBIGUOUS
    assert evaluation.fault_flag == POLICY_AMBIGUITY


def test_default_action_applies_when_no_rule_matches(org_snapshot) -> None:
    policy = ContainmentPolicy(default_action="escalate", rules=[])
    snapshot = org_snapshot.model_copy(update={"containment_policy": policy})
    target = resolve_host_target(host_bundle(host_id="ws-99"))
    assert target is not None
    evaluation = evaluate_target_containment_policy(snapshot, target)
    assert evaluation.action == PolicyAction.ESCALATE
    assert evaluation.fault_flag == CONTAINMENT_POLICY_ESCALATION_REQUIRED


def test_scoped_allow_overrides_default_escalate(org_snapshot) -> None:
    policy = ContainmentPolicy(
        default_action="escalate",
        rules=[
            ContainmentRule(
                name="allow_ws",
                action="allow",
                scope={"target_type": "host", "target_id": "ws-01"},
            ),
        ],
    )
    snapshot = org_snapshot.model_copy(update={"containment_policy": policy})
    allowed_target = resolve_host_target(host_bundle(host_id="ws-01"))
    assert allowed_target is not None
    assert (
        evaluate_target_containment_policy(snapshot, allowed_target).action
        == PolicyAction.ALLOW
    )
    other_target = resolve_host_target(host_bundle(host_id="ws-99"))
    assert other_target is not None
    other_eval = evaluate_target_containment_policy(snapshot, other_target)
    assert other_eval.action == PolicyAction.ESCALATE
    assert other_eval.fault_flag == CONTAINMENT_POLICY_ESCALATION_REQUIRED


def test_asset_group_allow_overrides_default_escalate(org_snapshot) -> None:
    """Operator story: escalate by default, allow this asset group."""
    policy = ContainmentPolicy(
        default_action="escalate",
        rules=[
            ContainmentRule(
                name="allow_eng_pool",
                action="allow",
                scope={"asset_id": "eng-workstation-pool"},
            ),
        ],
    )
    snapshot = org_snapshot.model_copy(update={"containment_policy": policy})
    pool_target = resolve_host_target(host_bundle(host_id="10.10.0.5"))
    assert pool_target is not None
    assert (
        evaluate_target_containment_policy(snapshot, pool_target).action
        == PolicyAction.ALLOW
    )
    outside_target = resolve_host_target(host_bundle(host_id="ws-99"))
    assert outside_target is not None
    outside_eval = evaluate_target_containment_policy(snapshot, outside_target)
    assert outside_eval.action == PolicyAction.ESCALATE
    assert outside_eval.fault_flag == CONTAINMENT_POLICY_ESCALATION_REQUIRED
