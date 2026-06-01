# Active Context

## Current focus

**Planning-only repo.** Implementation has not started (no `src/`, `pyproject.toml`, or `tests/` yet). All product/engineering truth lives in `docs/`.

**Next implementation milestone:** Phase 1 — Durable Walking Skeleton (`docs/plan.md` Tasks 1–12). First executable step: **Task 1** (repo structure + test harness).

**Hard gate:** `docs/contracts.md` must be treated as fixed before Task 3 (canonical hashing / ID derivation).

## Recently changed

- Memory Bank initialized from `docs/` (this session).
- Prior agent setup: `AGENTS.md`, `.cursor/rules/ultimate-agentic-workflow.mdc`, `memory-bank/` scaffold.

## Current blockers

- No application code or test harness — cannot run `pytest` or verify builds.
- Operator/docs referenced in plan but absent from repo: `docs/operator_runbook.md`, `docs/architecture.md`, `docs/eval_gates.md` (planned Task 35).
- Provisional alert-rate targets must be defined before Sprint 1 ends (plan Task 9 / 11) — values **TODO** in docs.

## Important notes for agents

1. Read `docs/contracts.md` before any hashing, feed checksum, or ID code.
2. Use `docs/plan.md` for task order, dependencies, and phase gates — do not skip Phase 1 durability core.
3. `standard_review` replaces `pass` everywhere (API, schema, persistence).
4. Outcome Matrix in `docs/contracts.md` §12 is what the eval harness must assert (mirror of spec).
5. Do not rewrite `docs/`; update Memory Bank when project state or phase changes.
6. For T3 work per `ultimate-agentic-workflow`, use `.workflow/<task-slug>/` Flight Recorder artifacts.
