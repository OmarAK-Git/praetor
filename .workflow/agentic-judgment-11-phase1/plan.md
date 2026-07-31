# agentic-judgment-11-phase1

## Goal
Implement Phase 1 source fan-out orchestration with per-source budgets.

## Scope
Phase 1 only; Phase 2/3 come next.

## Acceptance criteria
- Phase 1 fans out four source investigators concurrently with per-source BudgetTracker limits.
- Per-source failures degrade gracefully into the SessionEvidenceRegistry.
- Focused phase tests for Phase 1 pass.

## Files allowed
- src/praetor/judgment/agentic/phases.py
- tests/judgment/agentic/test_phases.py
- .workflow/agentic-judgment-11-phase1/

## Verification
- `pytest tests/judgment/agentic/test_phases.py -v`
- `ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py`
- `mypy src/praetor/judgment/agentic/phases.py`

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
