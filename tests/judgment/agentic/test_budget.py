"""Unit tests for PhaseBudget/BudgetTracker."""

from __future__ import annotations

import pytest

from praetor.judgment.agentic.budget import (
    BudgetExceededError,
    BudgetTracker,
    PhaseBudget,
)


def test_budget_tracker_allows_calls_up_to_max() -> None:
    tracker = BudgetTracker(budget=PhaseBudget(max_tool_calls=2, max_seconds=10.0))
    tracker.consume_call()
    tracker.consume_call()
    assert tracker.calls_made == 2


def test_budget_tracker_raises_when_exceeded() -> None:
    tracker = BudgetTracker(budget=PhaseBudget(max_tool_calls=1, max_seconds=10.0))
    tracker.consume_call()
    with pytest.raises(BudgetExceededError):
        tracker.consume_call()


def test_phase_budget_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="max_tool_calls"):
        PhaseBudget(max_tool_calls=-1, max_seconds=1.0)
    with pytest.raises(ValueError, match="max_seconds"):
        PhaseBudget(max_tool_calls=1, max_seconds=0.0)


def test_zero_call_budget_never_permits_a_call() -> None:
    tracker = BudgetTracker(budget=PhaseBudget(max_tool_calls=0, max_seconds=10.0))
    with pytest.raises(BudgetExceededError):
        tracker.consume_call()
