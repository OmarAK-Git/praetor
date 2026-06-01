# Review: TASK-008 (reopen hardening)

## Scope adherence

- Hardening pass only; no Task 9+ scope.
- No `docs/` modifications.
- Test fakes removed from production package.

## Fixes applied

1. `FailingJsonlSink` moved to `tests/alerts/_fakes.py`; removed from public API.
2. `SystemHealthAlert` docstring corrected: contract is emission payload; delivery tracking is SQLite outbox (DEC-026).
3. `_deliver_to_sink` catches all `Exception` (not `BaseException`); records `exception_type` in result.
4. Guards pinned: `record_delivery_attempt` PENDING → `ValueError`; unknown channel → `KeyError`.
5. FK regression test for orphan delivery-attempt rows.
6. Nested `critical_transaction` rejected for persist/emit/record (Task 9 boundary).
7. Duplicate `alert_id`: idempotent when payload matches; `DuplicateHealthAlertError` on conflict (DEC-027).
8. Fail → fail retry coverage; at-least-once JSONL duplicate test + module doc.
9. Direct `fetch_retryable_delivery_attempts` empty-list test.
10. Import-order smoke tests for DEC-025.
11. `_initialized_conn_ids` v1 lifetime documented.

## Gaps (documented, not hidden)

| Gap | Deferred to |
|-----|-------------|
| Startup outbox scan / recovery orchestration | TASK-011/012 |
| Breaker trip / emergency / config activation emitters | TASK-009+ |
| Actual SIEM/chat integrations | Future |
| Exactly-once JSONL | Not planned v1 |

## Doc ambiguity

Resolved: contract fields unchanged; outbox delivery shape lives in SQLite tables per spec, not on the Pydantic model.
