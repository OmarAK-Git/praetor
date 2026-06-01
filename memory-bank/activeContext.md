# Active Context

## Current focus

**TASK-002 next** — versioned contract models (`docs/plan.md` Task 2). TASK-001 complete.

**Hard gate:** `docs/contracts.md` must be treated as fixed before Task 3 (canonical hashing / ID derivation).

## Recently changed

- TASK-001: `pyproject.toml`, `src/praetor/__init__.py`, `tests/test_smoke.py`, fixture manifest stub.
- Human decisions locked: Python 3.11+, hatchling build backend.

## Current blockers

- None for Task 2 start (Task 1 satisfied).
- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Provisional alert-rate targets — **TODO** before Sprint 1 ends (Tasks 9 / 11).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. Use `docs/plan.md` for task order, dependencies, and phase gates.
3. `standard_review` replaces `pass` everywhere.
4. Do not rewrite `docs/`; update Memory Bank when project state changes.
5. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
