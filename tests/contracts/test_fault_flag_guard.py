"""Static guards for policy/engine fault-flag literals (V2-016)."""

from __future__ import annotations

from praetor.contracts.fault_flags import (
    CANONICAL_FAULT_FLAG_VALUES,
    assert_policy_engine_fault_literals_are_canonical,
    collect_policy_engine_fault_flag_literals,
    expected_system_fault_escalation,
)
from praetor.metrics.events import OutcomeMatrixFaultFlag


def test_policy_engine_fault_flag_literals_are_canonical_subset() -> None:
    assert_policy_engine_fault_literals_are_canonical()
    literals = collect_policy_engine_fault_flag_literals()
    assert literals, "expected at least one policy/engine fault-flag literal"
    for value in literals.values():
        assert value in CANONICAL_FAULT_FLAG_VALUES
        OutcomeMatrixFaultFlag(value)


def test_expected_system_fault_escalation_matches_outcome_matrix() -> None:
    assert expected_system_fault_escalation(
        [OutcomeMatrixFaultFlag.REVOCATION_FEED_UNHEALTHY.value]
    )
    assert not expected_system_fault_escalation(
        [OutcomeMatrixFaultFlag.NEVER_CONTAIN_SNAPSHOT.value]
    )
    assert not expected_system_fault_escalation(
        [
            OutcomeMatrixFaultFlag.NEVER_CONTAIN_LIVE_CONFLICT.value,
            OutcomeMatrixFaultFlag.TICKET_STAMP_FAILED.value,
        ]
    )
