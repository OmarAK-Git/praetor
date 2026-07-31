# agentic-judgment-03-budget-errors

## Goal
Add PhaseBudget/BudgetTracker and AgenticEvidenceGatheringFailedError.

## Scope
Budget + error types only; no phase orchestration yet.

## Acceptance criteria
- BudgetTracker permits up to max_tool_calls and raises BudgetExceededError beyond that, including zero-call budgets.
- PhaseBudget rejects invalid max_tool_calls/max_seconds.
- AgenticEvidenceGatheringFailedError is a ProviderError subclass.

## Files allowed
- src/praetor/judgment/agentic/budget.py
- src/praetor/judgment/agentic/errors.py
- tests/judgment/agentic/test_budget.py
- tests/judgment/agentic/test_errors.py
- .workflow/agentic-judgment-03-budget-errors/

## Verification
- `pytest tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py -v`
- `ruff check src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py`
- `mypy src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py`

## Tier
T2

## Researcher decision
skipped: single prescribed implementation path in plan; no multi-path opportunity cost

## Standing orders
- TDD: failing test first, then implement
- Do NOT commit
- Do NOT install dependencies
- Worktree root: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`
- Set `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src` for all python/pytest/mypy
- Single-shot provider / PolicyGate evaluation logic untouched
