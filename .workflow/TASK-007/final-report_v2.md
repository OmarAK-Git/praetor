# Final report: TASK-007

## Summary

TASK-007 reopen adds verification hardening only. Ten new tests cover ambiguous backend classification, pending-on-restart recovery, EMPTY_BUNDLE stamping, cached failed terminal behavior, payload authority on retry, DEC-022 additive schema upgrade, recovery-path idempotent backend replay, `record_stamp_outcome` PENDING guard, and `processing_attempt_identity` first-writer semantics (DEC-023). Implementation fix: `_is_backend_ambiguity` classifies transport/timeout errors as durable `unknown`; schema cache validates table existence before skip.

## Files changed

| Path | Change |
|------|--------|
| `src/praetor/tickets/stamp.py` | `_is_backend_ambiguity`; catch transport/timeout as `unknown` |
| `src/praetor/tickets/outbox.py` | `_stamp_table_exists`; safe per-conn schema cache |
| `tests/tickets/test_stamp_outbox.py` | +10 tests (21 total) |
| `memory-bank/decisions.md` | DEC-022 update, DEC-023 |
| `memory-bank/progress.md` | Reopen entry |
| `memory-bank/activeContext.md` | Reopen complete; Task 8 not started |
| `memory-bank/tasks.md` | Updated evidence count |
| `.workflow/TASK-007/*` | verification, traceability, review, final-report, state |

## Tests added (reopen)

1. `test_connection_error_records_unknown_after_pending_written`
2. `test_programmer_error_not_swallowed_leaves_pending`
3. `test_unknown_recovery_idempotent_on_same_backend_instance`
4. `test_pending_recovery_after_restart_uses_same_stamp_id`
5. `test_processing_attempt_identity_preserved_on_cross_attempt_recovery`
6. `test_execute_stamp_returns_cached_failed_without_backend_recall`
7. `test_empty_bundle_stamp_id_stable_on_unknown_recovery`
8. `test_retry_uses_durable_outbox_payload_not_fresh_context`
9. `test_task6_db_gains_stamp_table_without_schema_bump`
10. `test_record_pending_outcome_rejected_and_row_unchanged`

## Behavior corrected

- `ConnectionError`, `TimeoutError`, `StampTimeoutError`, and non-local `OSError` → durable `unknown` (not leaked, not `failed`)
- Programmer errors (`ValueError`, etc.) propagate; pending row unchanged
- Schema cache no longer skips DDL on recycled connection handles without table

## Checks

| Check | Result |
|-------|--------|
| `pytest -q tests/tickets/test_stamp_outbox.py` | pass (21 tests) |
| `pytest -q` | pass (173 tests) |
| `mypy src` | pass (34 files) |
| No `docs/` modifications | pass |

## Gaps remaining (deferred, not hidden)

| Gap | Deferred to |
|-----|-------------|
| Attempt FSM `pending_stamp` wiring | TASK-023 |
| PolicyGate / edict append / `ticket_stamp_failed` | TASK-023 |
| Outbox timestamp RFC3339 six-digit format for hashed fields | TASK-023 integration hazard |
| Generic `RuntimeError` → `unknown` | Not implemented (intentional boundary) |
| Startup outbox enumeration / recovery orchestration | TASK-011/012 |

## Follow-up

| Item | Owner | Notes |
|------|-------|-------|
| TASK-008 | blocked until reopen accepted | SystemHealthAlert outbox |
| TASK-023 | future | Stamp contract integration |

## Sign-off

- **Run status:** complete (verification hardening reopen)
- **Evidence fresh as of:** 2026-06-01
- **Safe to commit:** yes
