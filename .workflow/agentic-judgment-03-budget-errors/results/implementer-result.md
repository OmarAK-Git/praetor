# Implementer result — agentic-judgment-03-budget-errors

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/budget.py` | New: `PhaseBudget`, `BudgetTracker`, `BudgetExceededError` for per-phase tool-call budgeting |
| `src/praetor/judgment/agentic/errors.py` | New: `AgenticEvidenceGatheringFailedError(ProviderError)` for all-sources-fail escalation |
| `tests/judgment/agentic/test_budget.py` | New: 4 unit tests for budget tracker and validation (TDD step 1) |
| `tests/judgment/agentic/test_errors.py` | New: 1 unit test confirming error subclasses `ProviderError` (TDD step 5) |

## TDD evidence

1. **Budget tests (pre-implementation):** `pytest tests/judgment/agentic/test_budget.py -v` → `ModuleNotFoundError: No module named 'praetor.judgment.agentic.budget'`
2. **Budget tests (post-implementation):** 4 passed
3. **Errors tests (post-implementation):** 1 passed

## Verification commands

```
PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src pytest tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py -v
```
→ **5 passed** in 0.28s

```
ruff check src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py
```
→ **All checks passed!**

```
mypy src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py
```
→ **Success: no issues found in 2 source files**

## Acceptance criteria

- [x] `BudgetTracker` permits up to `max_tool_calls` and raises `BudgetExceededError` beyond that, including zero-call budgets
- [x] `PhaseBudget` rejects invalid `max_tool_calls` / `max_seconds`
- [x] `AgenticEvidenceGatheringFailedError` is a `ProviderError` subclass

## Gaps / notes

- No commit (per task instructions).
- Queue item not marked done (per task instructions).
- `max_seconds` is validated at construction but not enforced by `BudgetTracker` (by design per plan — advisory only; orchestration tracks call count).
