# Implementer packet — agentic-judgment-12-phase2-3

## Objective
Implement Phase 2 hypothesis debate and Phase 3 lead reconciliation with protected budgets.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/judgment/agentic/phases.py
- tests/judgment/agentic/test_phases.py
- .workflow/agentic-judgment-12-phase2-3/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- Phase 2 runs malicious and benign hypothesis cases over the registry without tools.
- Phase 3 has an independently protected budget and produces the final ModelJudgment surface needed by the provider.
- Focused phase tests cover Phase 2/3.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/judgment/agentic/test_phases.py -v`
- `ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py`
- `mypy src/praetor/judgment/agentic/phases.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
