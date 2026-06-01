# Verification: TASK-008

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | `pytest -q` | all pass | 196 passed | pass |
| V-002 | No `docs/` modifications | none | no docs/ changes | pass |
| V-003 | Persisted before delivery attempt | test passes | `test_health_alert_persisted_before_delivery_attempt` | pass |
| V-004 | JSONL + stdout statuses recorded | test passes | `test_jsonl_and_stdout_delivery_statuses_recorded` | pass |
| V-005 | Failed delivery retryable | test passes | `test_failed_delivery_remains_retryable` | pass |
| V-006 | Future channels without migration | test passes | `test_outbox_schema_supports_future_channels_without_migration` | pass |
| V-007 | `revocation_feed_unhealthy` supported | test passes | `test_revocation_feed_unhealthy_alert_supported` | pass |
| V-008 | Outbox-only (not in ledger tables) | test passes | `test_system_health_alert_is_outbox_only` | pass |
| V-009 | `critical_transaction` for writes | tests pass | nested-tx rejection tests | pass |
| V-010 | `mypy src` | pass | 37 source files, no issues | pass |
| V-011 | Additive schema from Task 7 DB | test passes | `test_task7_db_gains_health_alert_tables_without_schema_bump` | pass |
| V-012 | No test fakes in production API | `FailingJsonlSink` removed | `tests/alerts/_fakes.py` only | pass |
| V-013 | Contract docstring accurate | no lying deferral | `health.py` docstring updated (DEC-026) | pass |
| V-014 | Non-OSError sink failures recorded | test passes | `test_non_oserror_sink_failure_recorded_as_failed` | pass |
| V-015 | `record_delivery_attempt` PENDING guard | ValueError | `test_record_pending_outcome_rejected_and_row_unchanged` | pass |
| V-016 | Unknown channel KeyError | test passes | `test_record_unknown_channel_raises_key_error` | pass |
| V-017 | FK enforcement regression | IntegrityError | `test_delivery_attempt_foreign_key_rejects_orphan_alert_id` | pass |
| V-018 | No nested critical tx for emit/persist | StartupGuardError | nested-tx tests | pass |
| V-019 | Duplicate `alert_id` idempotency | same payload idempotent | `test_duplicate_alert_id_same_payload_is_idempotent` | pass |
| V-020 | Duplicate `alert_id` conflict | different payload error | `test_duplicate_alert_id_different_payload_raises` | pass |
| V-021 | Fail → fail retry stays failed | test passes | `test_fail_then_fail_retry_stays_failed` | pass |
| V-022 | JSONL at-least-once duplicate documented | test + module doc | `test_jsonl_at_least_once_duplicate_on_crash_before_record` | pass |
| V-023 | Fully succeeded not retryable | empty list | `test_fetch_retryable_empty_when_fully_succeeded` | pass |
| V-024 | Import-order smoke (DEC-025) | both orders | `TestImportOrderSmoke` | pass |
| V-025 | `ruff check` alerts modules | pass | all checks passed | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 reopen — `pytest -q tests/alerts/test_system_health_outbox.py` → 23 passed; `pytest -q` → 196 passed; `mypy src` pass; `ruff check src/praetor/alerts tests/alerts` pass
- **Overall:** pass (reopen hardening)

## Gaps / skipped (honest)

| Gap | Status | Notes |
|-----|--------|-------|
| Startup recovery enumeration / delivery worker | **deferred TASK-011/012** | Outbox + deliver API only |
| Breaker/emergency/config emitters | **deferred TASK-009+** | Callers not wired |
| SIEM/chat/ticket/SOAR channel implementations | **deferred future** | Schema supports via channel column |
| Exactly-once JSONL file output | **not implemented** | At-least-once documented; dedupe on `alert_id` |
