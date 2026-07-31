# agentic-judgment-05-ledger-history

## Goal
Add fetch_edicts_for_target_history ledger query helper for LedgerHistoryTool.

## Scope
Read-only ledger query helper + tests; no edict-append path changes.

## Acceptance criteria
- fetch_edicts_for_target_history returns matching DecisionEdicts by alert_reference or containment target_id.
- Query respects limit and does not invent new indexes beyond existing ledger fields.
- Focused ledger history tests pass.

## Files allowed
- src/praetor/ledger/store.py
- tests/ledger/test_target_history.py
- .workflow/agentic-judgment-05-ledger-history/

## Verification
- `pytest tests/ledger/test_target_history.py -v`
- `ruff check src/praetor/ledger/store.py tests/ledger/test_target_history.py`
- `mypy src/praetor/ledger/store.py`

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
