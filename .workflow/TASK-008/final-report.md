# Final report: TASK-008 (reopen hardening)

## Summary

TASK-008 reopen adds verification hardening only. Fourteen gaps from initial close are fixed or pinned: test fakes removed from production, contract docstring corrected, sink exception taxonomy widened, delivery/outbox guards tested, FK enforcement regression, nested critical-transaction boundary for Task 9, duplicate `alert_id` idempotency, fail→fail retry, at-least-once JSONL semantics, fully-succeeded retry query, critical-transaction tests (replacing code-review-only evidence), import-order smoke tests, and `_initialized_conn_ids` v1 documentation.

## Files changed

| Path | Change |
|------|--------|
| `src/praetor/alerts/system_health.py` | Remove test fake; widen sink exception handling; at-least-once doc |
| `src/praetor/alerts/outbox.py` | `DuplicateHealthAlertError`; idempotent persist; cache comment |
| `src/praetor/alerts/__init__.py` | Remove `FailingJsonlSink` export; add `DuplicateHealthAlertError` |
| `src/praetor/contracts/health.py` | Correct docstring (DEC-026) |
| `tests/alerts/_fakes.py` | New test doubles |
| `tests/alerts/test_system_health_outbox.py` | +14 tests (23 total) |
| `memory-bank/decisions.md` | DEC-026, DEC-027 |
| `memory-bank/*` | Reopen updates |
| `.workflow/TASK-008/*` | verification, review, final-report, state |

## Tests added (reopen)

1. `test_record_pending_outcome_rejected_and_row_unchanged`
2. `test_record_unknown_channel_raises_key_error`
3. `test_delivery_attempt_foreign_key_rejects_orphan_alert_id`
4. `test_write_pending_health_alert_rejects_nested_critical_transaction`
5. `test_emit_without_delivery_rejects_nested_critical_transaction`
6. `test_duplicate_alert_id_same_payload_is_idempotent`
7. `test_duplicate_alert_id_different_payload_raises`
8. `test_fail_then_fail_retry_stays_failed`
9. `test_jsonl_at_least_once_duplicate_on_crash_before_record`
10. `test_fetch_retryable_empty_when_fully_succeeded`
11. `test_non_oserror_sink_failure_recorded_as_failed`
12. `test_record_delivery_attempt_rejects_nested_critical_transaction`
13. `TestImportOrderSmoke` (2 tests)

## Behavior corrected

- Non-`OSError` sink failures → durable `failed` with `exception_type` (not leaked)
- Duplicate `alert_id` + matching payload → idempotent return
- Duplicate `alert_id` + different payload → `DuplicateHealthAlertError`
- Health alert persist/record cannot run inside an open critical transaction

## Checks

| Check | Result |
|-------|--------|
| `pytest -q tests/alerts/test_system_health_outbox.py` | pass (23 tests) |
| `pytest -q` | pass (196 tests) |
| `mypy src` | pass (37 files) |
| `ruff check src/praetor/alerts tests/alerts` | pass |
| No `docs/` modifications | pass |

## Gaps remaining (deferred)

| Gap | Deferred to |
|-----|-------------|
| Startup delivery worker / recovery enumeration | TASK-011/012 |
| Breaker/emergency/config emitters | TASK-009+ |
| Exactly-once JSONL file output | Not planned v1 |

## Sign-off

- **Run status:** complete (reopen hardening)
- **Evidence fresh as of:** 2026-06-01
- **Safe to commit:** yes
