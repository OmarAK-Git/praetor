# Review: TASK-007

## Review findings

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| R-001 | note | Attempt FSM transition to `pending_stamp` not wired | **Deferred TASK-023** |
| R-002 | note | Cached terminal success/failed skip backend re-call | Tested; correct per spec |
| R-003 | note | Outbox timestamps use `datetime.now(UTC).isoformat()` (+00:00) | **TASK-023 hazard** if copied into hashed edict/timing fields |
| R-004 | note | `RuntimeError` and other generic exceptions not classified as `unknown` | Intentional; only transport/timeout/OSError (non-local) |
| R-005 | note | `processing_attempt_identity` is first-writer only (DEC-023) | Documented; cross-attempt recovery does not update row |

**Severity:** `blocker` | `major` | `minor` | `note`

## Risks (post-review)

| Risk | Status |
|------|--------|
| Non-idempotent ticket backends double-stamp on unknown recovery | Documented in `stamp.py` constant + module doc |
| Outbox timestamp format incompatible with §1 RFC3336 if embedded in edict | Flagged for Task 23 integration |
| Recycled SQLite connection `id()` vs schema cache | Mitigated: cache validates table exists |

## Schema ensure (G-11)

`ensure_stamp_outbox_schema` caches per `id(conn)` but re-runs DDL when the table is missing (handles recycled connection handles). `open_state_store` still calls `init_stamp_outbox_schema` once at open; fetch/write paths call ensure defensively for direct module use.

## Human review notes

- **Reviewer:** agent (reopen hardening)
- **Date:** 2026-06-01
- **Decision:** approve pending fresh verification evidence

## Open items (explicitly deferred)

| Item | Owner | Notes |
|------|-------|-------|
| TASK-023 stamp sequencing | future | PolicyGate, edict append, `ticket_stamp_failed` flag |
| TASK-023 timestamp format | future | Use contracts §1 RFC3339 if outbox times enter hashed records |
| TASK-011/012 | future | Startup recovery / outbox enumeration |
