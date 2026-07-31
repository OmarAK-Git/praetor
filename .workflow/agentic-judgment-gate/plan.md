# agentic-judgment-gate

## Goal
Verify the complete agentic-judgment plan with repository-wide test, lint, and typecheck gates.

## Scope
Verify-only final plan gate; no feature implementation.

## Acceptance criteria
- Full pytest suite passes.
- Repository-wide ruff and mypy (src evals consumer_sdk) pass.
- All 14 task verifier artifacts exist.
- PolicyGate evaluation logic under src/praetor/policy/ shows zero diffs vs merge base for evaluation semantics (no gate logic edits).
- Single-shot FakeProvider/VertexProvider paths remain intact.

## Files allowed
- .workflow/agentic-judgment-gate/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

## Verification
- `pytest -q`
- `ruff check src tests evals consumer_sdk`
- `mypy src evals consumer_sdk`

## Tier
T3

## Researcher decision
skipped: gate is verify-only

## Standing orders
- TDD: failing test first, then implement
- Do NOT commit
- Do NOT install dependencies
- Worktree root: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`
- Set `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src` for all python/pytest/mypy
- Single-shot provider / PolicyGate evaluation logic untouched
