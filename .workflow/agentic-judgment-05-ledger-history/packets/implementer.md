# Implementer packet — agentic-judgment-05-ledger-history

## Objective
Add fetch_edicts_for_target_history ledger query helper for LedgerHistoryTool.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/ledger/store.py
- tests/ledger/test_target_history.py
- .workflow/agentic-judgment-05-ledger-history/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- fetch_edicts_for_target_history returns matching DecisionEdicts by alert_reference or containment target_id.
- Query respects limit and does not invent new indexes beyond existing ledger fields.
- Focused ledger history tests pass.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/ledger/test_target_history.py -v`
- `ruff check src/praetor/ledger/store.py tests/ledger/test_target_history.py`
- `mypy src/praetor/ledger/store.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
