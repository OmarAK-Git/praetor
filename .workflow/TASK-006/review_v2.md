# Review: TASK-006

## Gatekeeper fix pass (2026-06-01)

| # | Item | Resolution |
|---|------|------------|
| 1 | Feed sequence durability across reopen | `test_feed_sequence_survives_store_reopen` |
| 2 | Sequence rollback on failed revocation | `test_failed_revocation_does_not_consume_sequence` |
| 3 | Manual revocation rollback on key-clear failure | `test_manual_revocation_rolls_back_when_key_missing` |
| 4 | Completed-edict conflict path | `test_duplicate_insert_raises_conflict` |
| 5 | FSM negative coverage | Parametrized invalid transitions + terminal sink tests |
| 6 | Duplicate idempotency registration | `IdempotencyKeyConflictError` + `test_duplicate_registration_raises_conflict` |
| 7 | Abort + same-input retry | `test_aborted_allows_same_input_retry` (allowed, pinned) |
| 8 | Schema version | `verify_schema_version` + `test_rejects_incompatible_schema_version` |
| 9 | V-002 wording / branch | Renamed test; added mocked defensive re-check test; V-002 no longer claims wrong branch |
| 10 | `open_state_store` vs singleton | Docstring clarified; `test_open_state_store_does_not_acquire_singleton` |
| 11 | Test count | Corrected to **32** in artifacts |
| 12 | Test typing | `sqlite3` import, `Iterator[StateStore]` fixture |
| 13 | Missing read helpers | Deferred — gap recorded below |
| 14 | `_in_critical` / `id(conn)` | Out of scope (Task 5); recorded as non-blocking follow-up |

## Review findings

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| R-001 | note | Revocation rows durable in SQLite; ledger chain append is Task 10 | unchanged |
| R-002 | note | Full PRAGMA list deferred to Task 35 | unchanged |
| R-003 | note | No `list_non_terminal_attempts` / `list_pending_feed_outbox` helpers yet | Task 11/12 should add; avoid ad-hoc SQL |
| R-004 | note | `_in_critical` uses `id(conn)` — theoretical GC reuse false positive under single-writer | Task 5 follow-up if conn pooling added |

**Severity:** `blocker` | `major` | `minor` | `note`

## Risks (post-review)

| Risk | Status |
|------|--------|
| Ledger not yet chained | mitigated — Task 10 |
| Multi-handle `open_state_store` in tests | documented caller must hold singleton in production |

## Human review notes

- **Reviewer:** agent (verification fix pass)
- **Date:** 2026-06-01
- **Decision:** approve

## Open items

- Task 11/12 enumeration helpers (non-blocking for Task 6 sign-off)
