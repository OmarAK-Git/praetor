# Active Context

## Current focus

**TASK-003 next** — canonical serialization and hash constants (`docs/plan.md` Task 3). TASK-002 complete.

**Hard gate:** Implement hashing per `docs/contracts.md` §1–§8; no inline domain strings.

## Recently changed

- TASK-002: `src/praetor/contracts/` (14 Pydantic models), `schemas/*.json` artifacts, `tests/contracts/`, `pydantic>=2` in `pyproject.toml`.
- Flight Recorder: `.workflow/task-002/` complete.

## Current blockers

- None for Task 3 start (contracts exist).
- Operator docs still absent: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (Task 35).
- Provisional alert-rate targets — **TODO** before Sprint 1 ends (Tasks 9 / 11).

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. `docs/` are authoritative; `schemas/` are generated artifacts only.
3. `standard_review` replaces `pass` everywhere.
4. Do not rewrite `docs/`; update Memory Bank when project state changes.
5. Install/test: `pip install -e ".[dev]"` then `pytest` from repo root.
6. Regenerate schemas: `python -m praetor.contracts.schema_export`
