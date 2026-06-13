"""Canonical Outcome Matrix metadata for eval harness (docs/contracts.md §13).

Single source within evals/ for system_fault_escalation polarity; keyed by
``praetor.metrics.events.OutcomeMatrixFaultFlag``, not policy-module literals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from praetor.metrics.events import OutcomeMatrixFaultFlag

# §13 table: policy/safety-gate flags => false; infra/model/feed/queue/latency => true.
OUTCOME_MATRIX_SFE: dict[OutcomeMatrixFaultFlag, bool] = {
    OutcomeMatrixFaultFlag.CORRELATION_FAILURE: True,
    OutcomeMatrixFaultFlag.CONFIG_OVER_BUDGET: True,
    OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION: True,
    OutcomeMatrixFaultFlag.PROVIDER_MALFORMED_JSON: True,
    OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT: True,
    OutcomeMatrixFaultFlag.PROVIDER_REFUSAL: True,
    OutcomeMatrixFaultFlag.NEVER_CONTAIN_SNAPSHOT: False,
    OutcomeMatrixFaultFlag.NEVER_CONTAIN_LIVE_CONFLICT: False,
    OutcomeMatrixFaultFlag.AMBIGUOUS_TARGET_IDENTITY: False,
    OutcomeMatrixFaultFlag.ACCOUNT_CONTAINMENT_DISABLED: False,
    OutcomeMatrixFaultFlag.POLICY_AMBIGUITY: False,
    OutcomeMatrixFaultFlag.RATE_LIMIT_EXCEEDED: False,
    OutcomeMatrixFaultFlag.CONTAINMENT_BREAKER_OPEN: False,
    OutcomeMatrixFaultFlag.PROVIDER_HEALTH_BREAKER_OPEN: True,
    OutcomeMatrixFaultFlag.REVOCATION_FEED_UNHEALTHY: True,
    OutcomeMatrixFaultFlag.LATENCY_SLA_EXCEEDED: True,
    OutcomeMatrixFaultFlag.QUEUE_AGING_EXCEEDED: True,
    OutcomeMatrixFaultFlag.TICKET_STAMP_FAILED: False,
    OutcomeMatrixFaultFlag.LEDGER_CHAIN_INTEGRITY_FAILURE: False,
}

EXCLUDED_FROM_MATRIX_COMPLETENESS: frozenset[OutcomeMatrixFaultFlag] = frozenset(
    {
        OutcomeMatrixFaultFlag.LEDGER_CHAIN_INTEGRITY_FAILURE,
        OutcomeMatrixFaultFlag.TICKET_STAMP_FAILED,
    }
)

ESCALATE_PRODUCING_FAULT_FLAGS: frozenset[OutcomeMatrixFaultFlag] = frozenset(
    flag
    for flag in OutcomeMatrixFaultFlag
    if flag not in EXCLUDED_FROM_MATRIX_COMPLETENESS
)

REQUIRED_MATRIX_PAIRS: frozenset[tuple[str, bool]] = frozenset(
    (flag.value, OUTCOME_MATRIX_SFE[flag]) for flag in ESCALATE_PRODUCING_FAULT_FLAGS
)


def _pairs_from_expectations_block(
    block: Mapping[str, Any],
    *,
    prefix: str = "",
) -> list[tuple[str, bool]]:
    if str(block.get("final_disposition")) != "escalate":
        return []
    flags = block.get("fault_flags", [])
    if not isinstance(flags, list) or not flags:
        return []
    if "system_fault_escalation" not in block:
        msg = f"{prefix}escalate expectations must include system_fault_escalation"
        raise ValueError(msg)
    sfe = bool(block["system_fault_escalation"])
    return [(str(flag), sfe) for flag in flags]


def collect_scenario_matrix_pairs(
    *,
    runner: str,
    expectations: Mapping[str, Any],
) -> set[tuple[str, bool]]:
    pairs: set[tuple[str, bool]] = set()
    if runner == "revocation_feed_degraded_mode":
        for key in ("auto_contain", "standard_review"):
            block = expectations.get(key)
            if isinstance(block, Mapping):
                for flag, sfe in _pairs_from_expectations_block(
                    block, prefix=f"{key}: "
                ):
                    pairs.add((flag, sfe))
        return pairs

    for flag, sfe in _pairs_from_expectations_block(expectations):
        pairs.add((flag, sfe))
    return pairs


def collect_all_scenario_matrix_pairs(
    scenarios: Sequence[Any],
) -> set[tuple[str, bool]]:
    covered: set[tuple[str, bool]] = set()
    for scenario in scenarios:
        covered |= collect_scenario_matrix_pairs(
            runner=scenario.runner,
            expectations=scenario.expectations,
        )
    return covered


def scenario_asserts_ticket_stamp_failed(expectations: Mapping[str, Any]) -> bool:
    flags = expectations.get("fault_flags", [])
    if not isinstance(flags, list):
        return False
    return OutcomeMatrixFaultFlag.TICKET_STAMP_FAILED.value in flags
