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
        rules=[
            ContainmentRule(
                name="host_deny",
                action="deny",
                scope={"target_type": "host", "target_id": "ws-01"},
            ),
        ],
    )
    escalate_policy = ContainmentPolicy(
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
