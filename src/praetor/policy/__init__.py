"""Policy evaluation primitives."""

from praetor.policy.containment_policy import (
    ContainmentTarget,
    ContainmentTargetResolution,
    PolicyAction,
    resolve_containment_target,
    resolve_host_target,
)
from praetor.policy.gate import (
    PolicyGateEvaluation,
    evaluate_policy_gate,
    evaluation_to_policy_gate_result,
)
from praetor.policy.identity import (
    ACCOUNT_CONTAINMENT_DISABLED,
    AccountContainmentEvaluation,
    evaluate_account_containment_eligibility,
    is_sid_backed,
)

__all__ = [
    "ACCOUNT_CONTAINMENT_DISABLED",
    "AccountContainmentEvaluation",
    "ContainmentTarget",
    "ContainmentTargetResolution",
    "PolicyAction",
    "PolicyGateEvaluation",
    "evaluate_account_containment_eligibility",
    "evaluate_policy_gate",
    "evaluation_to_policy_gate_result",
    "is_sid_backed",
    "resolve_containment_target",
    "resolve_host_target",
]
