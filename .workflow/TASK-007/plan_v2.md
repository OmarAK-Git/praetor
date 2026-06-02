# Plan: TASK-007

## Goal

Deliver **Ticket Stamp Outbox** per `docs/plan.md` Task 7 and `docs/spec.md` § Ticket Stamp Contract and Outbox. Stamp outcomes are durable in SQLite keyed by stable `stamp_id`; pending is written before any external ticket call; timeout/ambiguous responses record `unknown` (distinct from `failed`); recovery retries reuse the same `stamp_id`.

**Authority:** `docs/spec.md` § Ticket Stamp Contract and Outbox; `docs/plan.md` Task 7; `docs/contracts.md` §5. Do not modify `docs/`.

## Scope

**In scope:**

- `src/praetor/tickets/outbox.py` — stamp outbox schema, pending write, outcome recording, fetch
- `src/praetor/tickets/stamp.py` — backend protocol, orchestration (pending → call → durable outcome), recovery retry
- `src/praetor/tickets/__init__.py` — exports
- `tests/tickets/test_stamp_outbox.py` — all Task 7 test-first criteria
- Minimal `open_state_store` hook to init stamp outbox schema
- Update `tests/contracts/test_scope_guard.py` to allow `tickets` package
- Flight Recorder + Memory Bank updates

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| PolicyGate / edict append integration | Task 23 |
| SystemHealthAlert outbox | Task 8 |
| Ledger append | Task 10 |
| Full decision flow / startup recovery | Task 12 |
| Docs | Any change under `docs/` |

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | Pending outbox entry written before external ticket call | `docs/plan.md` Task 7 |
| REQ-002 | Definite success/failure recorded durably | `docs/plan.md` Task 7, `docs/spec.md` |
| REQ-003 | Timeout/ambiguous records `unknown`, not `failed` | `docs/plan.md` Task 7, `docs/spec.md` |
| REQ-004 | Recovery retry uses same `stamp_id` (derived from three-tuple) | `docs/plan.md` Task 7, `docs/contracts.md` §5 |
| REQ-005 | Idempotent ticket backend treats duplicate `stamp_id` as no-op | `docs/plan.md` Task 7 |
| REQ-006 | Non-idempotent backend double-stamp risk documented | `docs/plan.md` Task 7, `docs/spec.md` |
| REQ-007 | `unknown` distinguishable from `failed` in stored status | `docs/plan.md` done-when |
| REQ-008 | Critical writes use `critical_transaction` | Task 5/6 pattern |
| REQ-009 | No `docs/` modifications | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema additive table without version bump | Old DBs missing table | `CREATE IF NOT EXISTS` on open; lazy ensure in outbox module |
| Non-idempotent backends | Double-stamp on unknown recovery | Document in `stamp.py`; idempotent contract is v1 default |
| Attempt lifecycle coupling deferred | Outbox without FSM transition | Task 7 scope is outbox durability; Task 23 wires sequencing |
| Scope guard blocks `tickets` package | CI fail | Update guard expected packages for Task 7 |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Workflow artifacts | — | plan, traceability, verification, state.json |
| T-002 | Tests first | T-001 | `tests/tickets/test_stamp_outbox.py` |
| T-003 | Implementation | T-002 | outbox.py, stamp.py, store hook |
| T-004 | Verification + Memory Bank | T-003 | pytest, mypy, review, final-report |

## Verification plan (summary)

- `pytest -q` all pass
- `mypy src` pass
- All six Task 7 test-first criteria covered
- `unknown` ≠ `failed` in API and persistence
- No `docs/` changes
- Record edict-append and attempt-FSM wiring gaps in review.md
