# Verification: TASK-006

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | At most one non-terminal attempt per `alert_identity` | second allocate fails | `test_at_most_one_non_terminal_per_alert` | pass |
| V-002 | Completed edict returned under `BEGIN IMMEDIATE` before allocation | no fresh attempt when tuple complete | `test_completed_tuple_returns_existing_under_critical_transaction` | pass |
| V-002b | Defensive re-check when active + completed coexist | mocked branch returns completed | `test_allocate_recheck_branch_when_active_and_completed_coexist` | pass |
| V-003 | Completed-edict uniqueness on three-tuple | duplicate insert raises `CompletedEdictConflictError` | `test_duplicate_insert_raises_conflict` | pass |
| V-004 | Attempt FSM enforced (terminal sinks, skips, backward) | parametrized invalid transitions | `test_invalid_forward_or_skip_rejected`, `test_*_terminal_sink` | pass |
| V-005 | Aborted allows changed-input retry | new attempt | `test_aborted_allows_changed_input_retry` | pass |
| V-005b | Aborted allows same-input retry (pinned) | new attempt, new identity | `test_aborted_allows_same_input_retry` | pass |
| V-006 | Manual revocation atomic + rollback on missing key | no partial rows | `test_manual_revocation_*`, `test_manual_revocation_rolls_back_when_key_missing` | pass |
| V-007 | Automated revocation retains key | key still active | `test_automated_revocation_retains_idempotency_key` | pass |
| V-008 | Failed revocation does not consume sequence | next seq reused | `test_failed_revocation_does_not_consume_sequence` | pass |
| V-009 | Feed sequence survives reopen | seq N+1 after close/reopen | `test_feed_sequence_survives_store_reopen` | pass |
| V-010 | Duplicate idempotency registration rejected | `IdempotencyKeyConflictError` | `test_duplicate_registration_raises_conflict` | pass |
| V-011 | Incompatible schema version rejected | `IncompatibleSchemaError` | `test_rejects_incompatible_schema_version` | pass |
| V-012 | `open_state_store` does not enforce singleton (documented) | two handles possible; doc mentions caller duty | `test_open_state_store_does_not_acquire_singleton` | pass |
| V-013 | No `docs/` modifications | scope guard | git diff docs/ empty | pass |
| V-014 | Full `pytest -q` | all pass | 152 passed in 2.84s | pass |
| V-015 | Task 6 test count | 32 collected | `pytest --collect-only` → 32 | pass |
| V-016 | `mypy src` | no errors | 31 files pass | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 (verification fix pass) — `pytest -q`, `pytest --collect-only tests/state/test_attempt_lifecycle.py`, `mypy src`
- **Overall:** pass

## Gaps / skipped checks

- Hash-chain ledger append for revocations (Task 10)
- Feed JSONL export and startup recovery (Tasks 11–12)
- Enumerators for non-terminal attempts / pending feed rows (Task 11/12 — recorded in review)
- `_in_critical` keyed by `id(conn)` — Task 5 follow-up, non-blocking (recorded in review)
- Full PRAGMA list from absent `docs/operator_runbook.md` (Task 35)
- `mypy tests/` — import-untyped noise from installed package layout; test file has explicit `sqlite3` import and `Iterator` fixture typing
