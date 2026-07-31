"""Per-phase execution budgets for the agentic judgment pipeline."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceededError(Exception):
    """Raised when a phase attempts to exceed its allotted tool-call budget."""


@dataclass(frozen=True)
class PhaseBudget:
    """Bounds one phase's tool-call volume. Wall-clock (max_seconds) is
    advisory here — a real model backend enforces its own deadline using
    this value; the orchestration layer only tracks call count."""

    max_tool_calls: int
    max_seconds: float

    def __post_init__(self) -> None:
        if self.max_tool_calls < 0:
            msg = "max_tool_calls must be non-negative"
            raise ValueError(msg)
        if self.max_seconds <= 0:
            msg = "max_seconds must be positive"
            raise ValueError(msg)


@dataclass
class BudgetTracker:
    """Tracks tool-call consumption against a PhaseBudget for one run."""

    budget: PhaseBudget
    calls_made: int = 0

    def consume_call(self) -> None:
        if self.calls_made >= self.budget.max_tool_calls:
            msg = f"tool-call budget exhausted: {self.budget.max_tool_calls}"
            raise BudgetExceededError(msg)
        self.calls_made += 1
