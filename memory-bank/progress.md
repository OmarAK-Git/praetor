# Progress Log

## 2026-06-01 — TASK-006 verification fix pass

- Added 20 tests: feed sequence reopen/rollback, manual revocation rollback, completed-edict conflict, FSM negatives, idempotency duplicate, schema version reject, abort same-input retry, singleton contract.
- Implementation: `IncompatibleSchemaError`, `IdempotencyKeyConflictError`, `verify_schema_version`, `read_feed_sequence_next`.
- Verification: `pytest -q` → 152 passed; Task 6 file → **32** tests collected; `mypy src` pass.
- Artifacts corrected (V-002 wording, test count).

## 2026-06-01 — TASK-006 complete

- **`src/praetor/state/`:** `store.py`, `attempts.py`, `completed_decisions.py`, `idempotency.py` — attempt FSM, three-tuple dedup, manual/automated revocation + feed outbox sequence.
- Tests: `tests/state/test_attempt_lifecycle.py` — 32 tests (after fix pass).
- Verification: `pytest -q` → 152 passed; `mypy src` → 31 files pass.
- Flight Recorder: `.workflow/TASK-006/`.
- Gap: ledger chain append (Task 10); feed export (Task 11); enumeration helpers (11/12).

## 2026-06-01 — TASK-005 reopen complete

- **DEC-017:** `init_state_dir` one-shot WAL bootstrap; guard verify-only.
- **DEC-018:** nested `critical_transaction` forbidden (per-connection sentinel).
- **DEC-019:** Windows `msvcrt.locking` ratified vs spec `CreateFile` wording.
- **`verify_synchronous`:** `REQUIRED_SYNCHRONOUS_MIN=1` (NORMAL).
- Tests: 28 startup guard + bare-BEGIN scope guard; 119 total `pytest`.
- Verification: `mypy src` → 27 files pass.
- Gap: process-exit wrapper deferred to Task 12.

## 2026-06-01 — TASK-005 complete

- **`src/praetor/runtime/singleton.py`:** OS-level singleton file lock (`flock` on POSIX, `msvcrt.locking` on Windows); held for process lifetime; non-zero exit code on contention.
- **`src/praetor/state/sqlite_guard.py`:** WAL journal mode verification, explicit `isolation_level=None`, `critical_transaction` with `BEGIN IMMEDIATE`, `run_startup_sqlite_guard` entry point.
- Tests: `tests/runtime/test_startup_guard.py` — 13 tests including subprocess second-process block.
- Verification: `pytest -q` → 107 passed; `mypy src/praetor/runtime src/praetor/state`; `ruff check` on new modules.
- Flight Recorder: `.workflow/TASK-005/`.
- Gap: full SQLite PRAGMA list deferred to absent `docs/operator_runbook.md` (Task 35).

## 2026-06-01 — TASK-004 complete

- **`src/praetor/auth/`:** `Principal`, role literals, `TokenVerifier`, three external surfaces, `verified_record_identity` (rejects self-asserted overrides), `guard_internal_only` + `authenticate_external_write` for internal-op enforcement.
- Tests: `tests/auth/test_auth_primitives.py` — 28 tests.
- Tooling: mypy/ruff added to dev deps; auth module passes strict mypy and ruff.
- Verification: `pytest -q` → 90 passed; `mypy src/praetor/auth`; `ruff check src/praetor/auth tests/auth`.
- Flight Recorder: `.workflow/TASK-004/`.

## 2026-06-01 — TASK-003 complete (doc-first correction)

- **`docs/contracts.md`:** added §5 `stamp_id` (four-part delimited hash over completed-edict three-tuple; stable across attempts for outbox recovery idempotency); ratified §7 `EMPTY_BUNDLE` preimage `praetor:v1:empty_bundle`; renumbered §6–§15.
- **`src/praetor/hashing/`:** canonical serialization; `derive_decision_id`, `derive_idempotency_key`, `derive_stamp_id` (three-tuple only), feed checksum, never-contain hash.
- Tests: `tests/hashing/test_canonical.py` — includes stamp stability across attempts; scope guard allows `docs/contracts.md` only.
- Verification: `pytest -q` → 62 passed.
- Flight Recorder: `.workflow/TASK-003/`.

## 2026-06-01 — TASK-002 complete

- Implemented 14 versioned Pydantic v2 contracts under `src/praetor/contracts/` with `extra=forbid`, Literal `schema_version` / `record_type`, and §10–§11 validators.
- Generated deterministic JSON Schema artifacts in `schemas/` (not authoritative).
- Tests: `tests/contracts/` — round-trip, negative validation, export stability, scope guard.
- Verification: `pytest -q` → 36 passed; `python -m praetor.contracts.schema_export`.
- Flight Recorder: `.workflow/task-002/`.

## 2026-05-31 — TASK-001 complete

- Implemented repo skeleton: `pyproject.toml` (hatchling, `requires-python >=3.11`), `src/praetor/`, smoke tests, fixture manifest stub.
- Verification: `pip install -e ".[dev]"`, `pytest -q` → 2 passed.
- Flight Recorder: `.workflow/task-001/` (plan, verification, review, final-report).

## 2026-05-31 — Memory Bank initialized

- Read authoritative planning docs: `docs/prd.md`, `docs/spec.md`, `docs/plan.md`, `docs/contracts.md`.
- Populated Memory Bank to summarize and index docs for agent operations.

## Project state

| Area | State |
|------|--------|
| Product definition | Complete in `docs/` |
| Implementation plan | Complete — 35 tasks in `docs/plan.md` |
| Package / tests | Task 1 done — `pytest` runs, `praetor` imports |
| Contracts | Task 2 done — `src/praetor/contracts/`, `schemas/` |
| Hashing | Task 3 done — `src/praetor/hashing/` + `docs/contracts.md` §1–§9 |
| Auth | Task 4 done — `src/praetor/auth/` |
| Runtime / startup guard | Task 5 done — `src/praetor/runtime/`, `src/praetor/state/sqlite_guard.py` |
| State store / lifecycle | Task 6 done — `src/praetor/state/{store,attempts,completed_decisions,idempotency}.py` |
| CI / eval harness | Not started (Task 26+) |
| Operator runbooks | Not in repo yet (Task 35) |

## Next recommended steps

1. TASK-007 — Ticket stamp outbox per `docs/plan.md`.
