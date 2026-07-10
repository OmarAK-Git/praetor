# Implementer Packet — V2-017 Production State Initialization Guard

## Objective

Ensure production startup owns table initialization invariants end to end: `open_production_state_store` under a held singleton creates or asserts all required policy tables without manual `init_*` calls.

## Original User Goal

V2-017 — Production state initialization guard: open_production_state_store under held singleton creates or asserts all required policy tables without manual init_* calls.

## Relevant Docs and State

- `docs/proposals/v2_implementation_plan.md` § V2-017
- `.workflow/_dream/playbook.digest.md`
- `memory-bank/activeContext.md`
- Existing state store and startup modules under `src/praetor/state/`, `src/praetor/runtime/`, `src/praetor/policy/state.py`

## Allowed Files

- `src/praetor/state/store.py`
- `src/praetor/runtime/startup.py`
- `src/praetor/policy/state.py`
- `tests/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`

## Do-Not-Touch Boundaries

- Do not mark the queue item done
- Do not run phase/sprint exit verification (`pytest -q`, full ruff/mypy)
- Stop and report before: dependency installs, `.codex`/`.claude` edits, clones, writes outside allowed files
- Do not implement V2-018 through V2-023 or V2 Gate 3 exit

## Acceptance Criteria

1. `open_production_state_store` under a held singleton creates or asserts all required policy tables.
2. Older additive DB fixtures get new tables through `CREATE TABLE IF NOT EXISTS` where allowed.
3. Incompatible schema version still rejects startup.
4. The verifier checks only V2-017 acceptance, not V2 Gate 3 completion.

## Verification Commands

```bash
pytest tests/ -q -k "production_state or state_store or startup or policy_state"
```

## Expected Result Schema

Write summary to `.workflow/v2-017-prod-state-init/results/implementer-result.md` with:

- Files changed
- How production table initialization is enforced
- Test additions
- Verification command output (pass/fail)
- Any approval gates hit (should be none)

## Implementation Hints

- Test first per V2 plan: singleton-held open creates/asserts policy tables; additive fixtures get new tables via `CREATE TABLE IF NOT EXISTS`; incompatible schema version rejects startup.
- Consolidate manual `init_*` calls into production startup path where appropriate.
- Keep changes scoped to state initialization only.
