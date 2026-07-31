# agentic-judgment-12-phase2-3

## Goal
Implement Phase 2 hypothesis debate and Phase 3 lead reconciliation with protected budgets.

## Scope
Phase 2/3 orchestration only; provider composition is Task 13.

## Acceptance criteria
- Phase 2 runs malicious and benign hypothesis cases over the registry without tools.
- Phase 3 has an independently protected budget and produces the final ModelJudgment surface needed by the provider.
- Focused phase tests cover Phase 2/3.

## Files allowed
- src/praetor/judgment/agentic/phases.py
- tests/judgment/agentic/test_phases.py
- .workflow/agentic-judgment-12-phase2-3/

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
