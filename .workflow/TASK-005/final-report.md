# Final report: TASK-005 (reopen)

## Summary

TASK-005 reopen closes gaps against `docs/spec.md` startup steps 1–2: fresh-install bootstrap via `init_state_dir`, synchronous PRAGMA verification, nested-transaction guard, BEGIN convention enforcement, lock race coverage, and documented Windows lock divergence (DEC-017–019). Guard still verify-only for journal mode; process exit remains exception `exit_code` until Task 12.

## Files changed

| Path | Change |
|------|--------|
| `memory-bank/decisions.md` | DEC-017, DEC-018, DEC-019 |
| `memory-bank/activeContext.md` | `init_state_dir` bootstrap note |
| `src/praetor/state/sqlite_guard.py` | `init_state_dir`, `verify_synchronous`, nested tx guard |
| `src/praetor/state/__init__.py` | New exports |
| `src/praetor/runtime/singleton.py` | In-bounds sentinel byte; contention-safe open |
| `tests/runtime/test_startup_guard.py` | 28 tests — bootstrap, sync, nested tx, lock race |
| `tests/contracts/test_scope_guard.py` | `test_no_bare_begin_outside_sqlite_guard` |
| `.workflow/TASK-005/*` | Updated verification, review, final-report |

## Checks

| Check | Result |
|-------|--------|
| `pytest -q` | pass (119 tests) |
| `mypy src` | pass (27 files) |
| Uninitialized DB rejected | pass — `test_run_startup_guard_rejects_uninitialized_db` |
| `synchronous=OFF` rejected | pass — `test_synchronous_off_rejected` asserts `exit_code` |
| Nested `critical_transaction` rejected | pass — outer tx intact |
| Sentinel cleared after rollback | pass — subsequent tx commits |
| Bare BEGIN outside guard | pass — AST scope guard |
| Two-process race | pass — exactly one winner |
| No `docs/` modifications | pass |

## Gaps / skipped checks

- Process-exit wrapper not built (Task 12) — exceptions expose `exit_code` only
- `foreign_keys=ON` verification deferred to Task 6
- Full PRAGMA list deferred to Task 35 operator runbook
- Full-repo ruff — pre-existing line-length issues in older tests

## Follow-up

| Item | Owner | Notes |
|------|-------|-------|
| TASK-006 | next agent | State store; call `init_state_dir` before first guard |
| TASK-012 | future | Application entrypoint maps guard errors to `sys.exit(exit_code)` |
| Operator runbook PRAGMA list | Task 35 | Extend guard beyond WAL + synchronous |

## Sign-off

- **Run status:** complete (reopen)
- **Evidence fresh as of:** 2026-06-01
- **Safe to commit:** yes (two-commit split per reopen instructions)
