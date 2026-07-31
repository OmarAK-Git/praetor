# Implementer packet — agentic-judgment-03-budget-errors

## Objective
Add PhaseBudget/BudgetTracker and AgenticEvidenceGatheringFailedError.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/judgment/agentic/budget.py
- src/praetor/judgment/agentic/errors.py
- tests/judgment/agentic/test_budget.py
- tests/judgment/agentic/test_errors.py
- .workflow/agentic-judgment-03-budget-errors/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- BudgetTracker permits up to max_tool_calls and raises BudgetExceededError beyond that, including zero-call budgets.
- PhaseBudget rejects invalid max_tool_calls/max_seconds.
- AgenticEvidenceGatheringFailedError is a ProviderError subclass.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py -v`
- `ruff check src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py`
- `mypy src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
