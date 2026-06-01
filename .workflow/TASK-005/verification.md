# Verification: TASK-005

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | Singleton lock acquired on empty state dir | success | pass | pass |
| V-002 | Second acquire in-process fails | `SingletonLockError` with non-zero `exit_code` | pass, exit_code=1 | pass |
| V-003 | Non-WAL journal mode rejected | `StartupGuardError` with non-zero `exit_code` | pass, exit_code=2 | pass |
| V-004 | `init_state_dir` persists WAL; idempotent | verify_journal_mode after reopen | pass | pass |
| V-005 | Uninitialized DB rejected by startup guard | `StartupGuardError` | pass | pass |
| V-006 | `synchronous=OFF` rejected | `StartupGuardError` with non-zero `exit_code` | pass | pass |
| V-007 | `synchronous=NORMAL` and FULL accepted | no raise | pass | pass |
| V-008 | WAL mode accepted; isolation explicit | connection opens | pass | pass |
| V-009 | `critical_transaction` uses BEGIN IMMEDIATE | insert/commit verified | pass | pass |
| V-010 | Nested `critical_transaction` forbidden | `StartupGuardError` | pass | pass |
| V-011 | Sentinel cleared after rollback | subsequent tx works | pass | pass |
| V-012 | Lock remains held while holder alive | second acquire fails | pass | pass |
| V-013 | Subprocess blocked while parent holds lock | child `sys.exit(exc.exit_code)` | pass (returncode=1) | pass |
| V-014 | Release allows in-process and subprocess reacquire | pass | pass | pass |
| V-015 | Two-process race: exactly one winner | xor returncode 0 / 1 | pass | pass |
| V-016 | No bare BEGIN outside `sqlite_guard.py` | AST scope guard | pass | pass |
| V-017 | No `docs/` modifications | scope guard | pass | pass |
| V-018 | Full `pytest -q` | all pass | 119 passed in 0.89s | pass |
| V-019 | `mypy src` (full repo) | no errors | 27 files pass | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 (TASK-005 reopen) — `pytest -q`, `mypy src`
- **Overall:** pass

## Gaps / skipped checks

- Process exit wrapper (map `exit_code` → `sys.exit`) owned by Task 12 — exceptions carry `exit_code`; production code does not exit yet
- Full SQLite PRAGMA list (incl. `foreign_keys`) deferred to `docs/operator_runbook.md` (Task 35) and Task 6 FK usage confirmation
- Full-repo `ruff check src tests` — pre-existing line-length issues outside new modules
