"""Canonical Outcome Matrix metadata for eval harness (docs/contracts.md §13).

Single source within evals/ for system_fault_escalation polarity; keyed by
``praetor.metrics.events.OutcomeMatrixFaultFlag``, not policy-module literals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from praetor.contracts.fault_flags import (
    OUTCOME_MATRIX_SFE as _CONTRACTS_OUTCOME_MATRIX_SFE,
)
from praetor.metrics.events import OutcomeMatrixFaultFlag

# Re-export canonical SFE polarity from contracts to keep eval harness aligned.
OUTCOME_MATRIX_SFE: dict[OutcomeMatrixFaultFlag, bool] = dict(_CONTRACTS_OUTCOME_MATRIX_SFE)

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
