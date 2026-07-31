# Implementer result — agentic-judgment-05-ledger-history

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/ledger/store.py` | Added `fetch_edicts_for_target_history` query helper using existing `ledger_chain` fields (`alert_reference`, `containment_directive.target_id`) with JSON extract; no new schema/indexes. |
| `tests/ledger/test_target_history.py` | TDD tests for alert-reference match, containment target match, and limit enforcement. |

## TDD sequence

1. Wrote failing tests first.
2. Confirmed `ImportError: cannot import name 'fetch_edicts_for_target_history'`.
3. Implemented query helper per plan.
4. All tests pass.

## Verification commands

```
PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src pytest tests/ledger/test_target_history.py -v
```
**Result:** 3 passed in 0.47s

```
PYTHONPATH=... ruff check src/praetor/ledger/store.py tests/ledger/test_target_history.py
```
**Result:** All checks passed!

```
PYTHONPATH=... mypy src/praetor/ledger/store.py
```
**Result:** Success: no issues found in 1 source file

## Gaps / notes

- No commit (per standing orders).
- Minor ruff fixes applied to test imports (consolidated `praetor.ledger.store` imports, removed unused `pytest` import, line-length wrap) — behavior unchanged.
- Task 6 (`LedgerHistoryTool`) is the sole consumer; not in scope for this task.
