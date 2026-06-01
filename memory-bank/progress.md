# Progress Log

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
| Hashing | Not started (Task 3) |
| CI / eval harness | Not started (Task 26+) |
| Operator runbooks | Not in repo yet (Task 35) |

## Next recommended steps

1. TASK-003 — canonical hashing per `docs/contracts.md`.
