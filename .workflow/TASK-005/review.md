# Review: TASK-005 (reopen)

## Review findings

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| R-001 | blocker | Fresh install: empty DB reports `journal_mode=delete`; guard rejected boot | `init_state_dir` one-shot bootstrap (DEC-017); guard stays verify-only |
| R-002 | blocker | `synchronous=OFF` passed guard; breaks ledger/outbox durability | `verify_synchronous` with `REQUIRED_SYNCHRONOUS_MIN=1` (DEC-017 scope) |
| R-003 | major | "Exit non-zero" overclaimed — only `exit_code` on exceptions | verification.md corrected; Task 12 owns process-exit wrapper |
| R-004 | major | Bare `BEGIN` outside guard not enforced | AST scope guard test added |
| R-005 | major | Nested `critical_transaction` silent corruption risk | Forbidden via per-connection sentinel (DEC-018) |
| R-006 | minor | Lock release/reacquire and race untested | Three new subprocess/in-process tests |
| R-007 | note | Windows `msvcrt.locking` vs spec `CreateFile` wording | DEC-019 ratified; in-bounds sentinel byte before lock |

**Severity:** `blocker` | `major` | `minor` | `note`

## Risks (post-review)

| Risk | Status |
|------|--------|
| `foreign_keys=ON` not verified yet | Deferred to Task 6 per reopen scope |
| Full PRAGMA list in absent operator runbook | TODO in `sqlite_guard.py`; Task 35 |
| `synchronous` is per-connection — guard runs at connect time on defaults | Accepted; OFF on active guarded conn caught by `verify_synchronous` |

## Human review notes

- **Reviewer:** human (reopen prompt)
- **Date:** 2026-06-01
- **Decision:** changes requested → implemented

## Open items

- Task 12: wire startup sequence with `sys.exit(exc.exit_code)` at application entrypoint
