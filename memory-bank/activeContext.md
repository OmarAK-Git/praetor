# Active Context

## Current focus

**TASK-007 verification hardening complete** — awaiting sign-off before TASK-008. Do not start Task 8 until TASK-007 reopen is accepted.

**Hard gate:** Three role-tagged external surfaces exist; ledger/feed/directive emission remain internal-only. Startup singleton + WAL guard operational.

## Recently changed

- TASK-007 reopen: ambiguous backend errors → `unknown`; 10 new hardening tests; DEC-023 processing_attempt_identity semantics.
- TASK-007: `src/praetor/tickets/{outbox,stamp}.py` — durable stamp outbox keyed by `stamp_id`; pending-before-call; `unknown` vs `failed`; recovery retry.
- TASK-006: `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` — attempt lifecycle, completed-edict three-tuple, revocation + feed outbox.
- TASK-005: `src/praetor/runtime/singleton.py`, `src/praetor/state/sqlite_guard.py` — OS singleton lock, WAL/isolation/BEGIN IMMEDIATE startup guard.
- Flight Recorder: `.workflow/TASK-006/` complete.
- TASK-004: `src/praetor/auth/` — authenticated write surfaces.

## Current blockers

- None for Task 8 start.
- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Provisional alert-rate targets — **TODO** before Sprint 1 ends (Tasks 9 / 11).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. **`stamp_id` (§5):** completed-edict three-tuple + `DOMAIN_STAMP_ID` — **no** `processing_attempt_identity`.
3. **`EMPTY_BUNDLE` (§7):** preimage exactly `praetor:v1:empty_bundle`; hash baked into correlation-failure IDs.
4. Hash/ID pins that feed derivations require **doc update in the same task** before code — not follow-up tickets.
5. `docs/contracts.md` is SSOT; `schemas/` are generated artifacts only.
6. Domain constants live only in `src/praetor/hashing/domains.py`.
7. Auth: external surfaces via `authenticate_*` functions; token issuance is operator-supplied (`TokenVerifier` protocol).
8. Startup: acquire `SingletonLock(state_dir)` first; call `init_state_dir(db_path)` once on fresh deploy; then `run_startup_sqlite_guard(db_path, singleton=lock)`; open lifecycle via `open_state_store(db_path)`; critical writes use `critical_transaction(conn)`.
9. State store is v1 single-writer — one process with singleton lock; `allocate_attempt` / revocation paths require that constraint.
10. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
11. Ticket stamp: `derive_stamp_id` from three-tuple; `execute_stamp` writes pending before backend call; transport/timeout ambiguity → `unknown` (not `failed`); recovery resends same `stamp_id` with durable payload; `processing_attempt_identity` is first-writer only (DEC-023).
