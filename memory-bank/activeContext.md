# Active Context

## Current focus

**TASK-006 next** — SQLite state store and attempt lifecycle (`docs/plan.md` Task 6). TASK-005 complete.

**Hard gate:** Three role-tagged external surfaces exist; ledger/feed/directive emission remain internal-only. Startup singleton + WAL guard operational.

## Recently changed

- TASK-005: `src/praetor/runtime/singleton.py`, `src/praetor/state/sqlite_guard.py` — OS singleton lock, WAL/isolation/BEGIN IMMEDIATE startup guard.
- Flight Recorder: `.workflow/TASK-005/` complete.
- TASK-004: `src/praetor/auth/` — authenticated write surfaces.

## Current blockers

- None for Task 6 start.
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
8. Startup: acquire `SingletonLock(state_dir)` first; call `init_state_dir(db_path)` once on fresh deploy (WAL bootstrap — verify-only guard does not auto-migrate); then `run_startup_sqlite_guard(db_path, singleton=lock)`; critical writes use `critical_transaction(conn)`.
9. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
