# Plan: TASK-012 — Walking Skeleton Decision Flow and Recovery

## Goal

Deliver minimal end-to-end decision intake, ledger append, stamp integration, and startup recovery per `docs/plan.md` Task 12 and `docs/spec.md` § Durable Lifecycle / startup steps 4–7.

**Authority:** `docs/plan.md` Task 12, `docs/spec.md` § startup recovery, `docs/contracts.md` §3.3, §7, Outcome Matrix rows for correlation/config/citation faults.

## Tier

T3 — Flight Recorder workflow. Executing-plans: implement tests-first paths from plan.md.

## Scope

**In scope:**

- `src/praetor/engine/{ids,recovery,orchestrator}.py`
- `run_engine_startup_recovery` wired from `open_state_store` after feed hook
- Ledger append for recovery revocations (audit gap from Task 11)
- `tests/engine/test_walking_skeleton.py`, `tests/engine/test_crash_recovery.py`
- `tests/contracts/test_scope_guard.py` — allow `engine` package

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| `docs/` edits | Command hard limit |
| Real correlator / PolicyGate / FakeProvider | Tasks 13–17 |
| Containment directive emission | Recovery and skeleton never emit `auto_contain` |
| Process-exit wrapper | Deferred (Task 5 gap) |

## Design

1. **Walking skeleton data** — fixed evidence catalog, bundle, and `ModelJudgment`; bundle hashed via canonical algorithm.
2. **Intake** — allocate → active → correlate (stub) → budget check → citation check → hardcoded judgment → skeleton policy (no `auto_contain`) → stamp → ledger append (`DecisionEdict` + `NeverContainSnapshotRecord`) → complete.
3. **Fault paths** — `correlation_failure` (EMPTY_BUNDLE, abort); `config_over_budget` (no judgment provider call); `invalid_model_citation` (escalate).
4. **Recovery** — enumerate non-terminal attempts; early states → abort; `pending_stamp` → stamp retry; `stamp_resolved`/`ready_to_append` → append safe edict from stamp status; scan outstanding directives vs live never-contain + ledger append revocations.
5. **ids.py** — single substitution site for EMPTY_BUNDLE in decision_id inputs.

## Verification plan

- `pytest -q tests/engine/`
- `pytest -q`
- `mypy src/praetor/engine`
- `ruff check src/praetor/engine tests/engine`

## Risks

| Risk | Mitigation |
|------|------------|
| Scope guard blocks `engine` | Update allowed package set |
| Recovery emits containment | Hard rule: final_disposition never `auto_contain` in recovery builder |
| Nested critical_transaction | Use in-transaction helpers from store/config patterns |
