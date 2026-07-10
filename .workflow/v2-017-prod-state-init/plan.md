# Workflow Plan — V2-017 Production State Initialization Guard

## Goal

V2-017 — Production state initialization guard: open_production_state_store under held singleton creates or asserts all required policy tables without manual init_* calls.

## Scope

Production startup table initialization only. Do not run V2 Gate 3 exit.

## Tier

T2

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

## Acceptance Criteria

1. `open_production_state_store` under a held singleton creates or asserts all required policy tables.
2. Older additive DB fixtures get new tables through `CREATE TABLE IF NOT EXISTS` where allowed.
3. Incompatible schema version still rejects startup.
4. The verifier checks only V2-017 acceptance, not V2 Gate 3 completion.

## Verification Commands

```bash
pytest tests/ -q -k "production_state or state_store or startup or policy_state"
```
