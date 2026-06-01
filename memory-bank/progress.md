# Progress Log

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
| CI / eval harness | Not started (Task 26+) |
| Operator runbooks | Not in repo yet (Task 35) |

## Next recommended steps

1. TASK-005 — SQLite startup guard and process singleton per `docs/plan.md`.
