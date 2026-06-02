# Final report: TASK-006

## Summary

TASK-006 delivers the SQLite state store and processing-attempt lifecycle per `docs/plan.md` Task 6: partial unique index for one non-terminal attempt per `alert_identity`, completed-edict three-tuple uniqueness, FSM transitions with abort, intake-race re-check after lock, and revocation writes (`DirectiveRevocationRecord` JSON + gap-free feed outbox sequence) with idempotency key clear on manual revocation only. All paths use Task 5 `critical_transaction`.

## Files changed

| Path | Change |
|------|--------|
| `src/praetor/state/store.py` | Schema, `StateStore`, revocation writers |
| `src/praetor/state/attempts.py` | Allocation, transitions, completion, abort |
| `src/praetor/state/completed_decisions.py` | Three-tuple completed edict table |
| `src/praetor/state/idempotency.py` | Active idempotency keys |
| `src/praetor/state/__init__.py` | Public exports |
| `tests/state/test_attempt_lifecycle.py` | 13 Task 6 tests |
| `memory-bank/tasks.md` | TASK-006 done |
| `memory-bank/activeContext.md` | TASK-007 next |
| `memory-bank/progress.md` | TASK-006 entry |
| `memory-bank/decisions.md` | DEC-020 |
| `.workflow/TASK-006/*` | Flight Recorder complete |

## Checks

| Check | Result |
|-------|--------|
| `pytest -q` | pass (132 tests) |
| `mypy src` | pass (31 files) |
| No `docs/` modifications | pass |

## Gaps / skipped checks

- Ledger hash-chain append for revocations deferred to Task 10
- Feed JSONL exporter and startup recovery deferred to Tasks 11–12
- Full SQLite PRAGMA list deferred to absent `docs/operator_runbook.md` (Task 35)
- Live two-thread allocation race not exercised (serialized re-check tests used)

## Follow-up

| Item | Owner | Notes |
|------|-------|-------|
| TASK-007 | next agent | Ticket stamp outbox; uses `stamp_id` + lifecycle |
| TASK-010 | future | Append `DirectiveRevocationRecord` to hash chain |
| TASK-011 | future | Export `revocation_feed_outbox` rows |

## Sign-off

- **Run status:** complete
- **Evidence fresh as of:** 2026-06-01
- **Safe to commit:** yes
