# Verification: TASK-007

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | `pytest -q` | all pass | 173 passed | pass |
| V-002 | No `docs/` modifications | none | no docs/ changes | pass |
| V-003 | Pending written before external call | test passes | `test_pending_outbox_written_before_backend_invoked` | pass |
| V-004 | Success/failure durable | test passes | `test_success_recorded_durably`, `test_failure_recorded_durably` | pass |
| V-005 | Timeout → `unknown` | explicit timeout only | `test_timeout_records_unknown_not_failed` | pass |
| V-005b | Transport/ambiguous backend → `unknown` | not failed, not leaked | `test_connection_error_records_unknown_after_pending_written` | pass |
| V-005c | Programmer errors not swallowed | exception propagates; row stays pending | `test_programmer_error_not_swallowed_leaves_pending` | pass |
| V-006 | Recovery retry same `stamp_id` | test passes | `test_unknown_recovery_resends_same_stamp_id`, pending restart test | pass |
| V-006b | Pending-on-restart recovery | single row, same stamp_id | `test_pending_recovery_after_restart_uses_same_stamp_id` | pass |
| V-006c | Recovery idempotent backend replay | same backend instance | `test_unknown_recovery_idempotent_on_same_backend_instance` | pass |
| V-007 | Idempotent fake backend duplicate `stamp_id` | direct + cached success | idempotent + cached-success tests | pass |
| V-007b | Cached failed terminal short-circuit | no backend re-call | `test_execute_stamp_returns_cached_failed_without_backend_recall` | pass |
| V-008 | Non-idempotent backend risk documented | doc/constant present | `NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK` | pass |
| V-009 | `unknown` distinguishable from `failed` | test + enum | dedicated timeout/connection tests | pass |
| V-010 | `mypy src` | pass | 34 source files, no issues | pass |
| V-011 | EMPTY_BUNDLE stamp path | stable retry | `test_empty_bundle_stamp_id_stable_on_unknown_recovery` | pass |
| V-012 | Payload authority on retry | durable payload A | `test_retry_uses_durable_outbox_payload_not_fresh_context` | pass |
| V-013 | DEC-022 additive schema | Task 6 DB upgrades | `test_task6_db_gains_stamp_table_without_schema_bump` | pass |
| V-014 | `record_stamp_outcome` PENDING guard | ValueError | `test_record_pending_outcome_rejected_and_row_unchanged` | pass |
| V-015 | `processing_attempt_identity` semantics | first-writer preserved | `test_processing_attempt_identity_preserved_on_cross_attempt_recovery` | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 reopen — `pytest -q tests/tickets/test_stamp_outbox.py` → 21 passed; `pytest -q` → 173 passed; `mypy src` pass
- **Overall:** pass (reopen hardening)

## Gaps / skipped (honest)

| Gap | Status | Notes |
|-----|--------|-------|
| Attempt FSM / PolicyGate / edict append | **deferred TASK-023** | Not in Task 7 scope |
| Outbox timestamp RFC3339 six-digit format | **deferred TASK-023** | `isoformat()` OK for outbox-only; hazard if copied into hashed edict fields |
| Generic `RuntimeError` → unknown | **not implemented** | Only transport/timeout/OSError (non-local) classified; intentional boundary |
| Startup recovery enumeration | **deferred TASK-011/012** | |
| ruff | skipped | not in verification plan |
