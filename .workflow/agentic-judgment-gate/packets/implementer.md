# Implementer packet — agentic-judgment-gate

## Objective
Verify the complete agentic-judgment plan with repository-wide test, lint, and typecheck gates.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- .workflow/agentic-judgment-gate/
- memory-bank/tasks.md
- memory-bank/progress.md
- memory-bank/activeContext.md

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- Full pytest suite passes.
- Repository-wide ruff and mypy (src evals consumer_sdk) pass.
- All 14 task verifier artifacts exist.
- PolicyGate evaluation logic under src/praetor/policy/ shows zero diffs vs merge base for evaluation semantics (no gate logic edits).
- Single-shot FakeProvider/VertexProvider paths remain intact.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest -q`
- `ruff check src tests evals consumer_sdk`
- `mypy src evals consumer_sdk`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
