# Verifier packet — agentic-judgment-03-budget-errors

## Goal
Add PhaseBudget/BudgetTracker and AgenticEvidenceGatheringFailedError.

## Acceptance criteria
- BudgetTracker permits up to max_tool_calls and raises BudgetExceededError beyond that, including zero-call budgets.
- PhaseBudget rejects invalid max_tool_calls/max_seconds.
- AgenticEvidenceGatheringFailedError is a ProviderError subclass.

## Changed files
- src/praetor/judgment/agentic/budget.py
- src/praetor/judgment/agentic/errors.py
- tests/judgment/agentic/test_budget.py
- tests/judgment/agentic/test_errors.py

## Commands (PYTHONPATH=worktree/src)
- pytest tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py -v
- ruff check src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py
- mypy src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py

## Implementer result
`.workflow/agentic-judgment-03-budget-errors/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-03-budget-errors/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Ignore phase-level gaps (no orchestration in this task). Confirm `git diff HEAD -- src/praetor/policy/` has no content changes. Write verifier-result.md.
