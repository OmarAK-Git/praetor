# Final Report: TASK-017

## Summary

Complete. TASK-017 delivers Deterministic PolicyGate v1 as a testable module with startup recovery step 6, production singleton entrypoint, and 29 focused policy tests. `auto_contain` requires passing citation, never-contain, identity, feature-gate, policy, feed-health, idempotency, rate-limit, and breaker checks inside a single `critical_transaction` on the emit path.

Post-review follow-ups resolved in this phase:

- **4A (record-only):** DEC-028 in `memory-bank/decisions.md` — gate = pure evaluator, engine = single serializable emit transaction at wiring time (hard acceptance criterion in plan; gate internal transaction unchanged for TASK-017 isolation).
- **4B (contracts carve-out):** Expired-directive re-issue is a fresh directive (same idempotency key, no supersession, no revocation record). Carve-out lives in `docs/contracts.md` §4.2 and `docs/plan.md` Task 17; `docs/spec.md` is frozen this phase (scope guard).

Engine wiring remains the known follow-on.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001–014 | `tests/policy/test_policy_gate.py`, `tests/policy/test_containment_policy.py`, `tests/policy/test_directive_embedded_hash.py` |
| REQ-015 | `run_engine_startup_recovery` → `reconcile_policy_state`; `tests/policy/test_policy_state_recovery.py` |
| REQ-016 | `test_production_entrypoint_*` |

## Files changed

- `src/praetor/policy/gate.py` (4B: remove expired supersession derivation)
- `src/praetor/policy/containment_policy.py`
- `src/praetor/policy/directive_builder.py`
- `src/praetor/policy/state.py`
- `src/praetor/policy/identity.py`
- `src/praetor/policy/__init__.py`
- `src/praetor/engine/recovery.py`
- `src/praetor/runtime/startup.py`
- `src/praetor/runtime/__init__.py`
- `src/praetor/config/directives.py`
- `src/praetor/state/store.py` (comment)
- `tests/policy/test_policy_gate.py` (4B: fresh re-issue test)
- `tests/policy/test_containment_policy.py`
- `tests/policy/test_policy_state_recovery.py`
- `tests/policy/test_directive_embedded_hash.py`
- `tests/policy/conftest.py`
- `docs/contracts.md` (§4.2 expired vs supersession carve-out)
- `docs/plan.md` (Task 17 criterion aligned)
- `memory-bank/decisions.md` (DEC-028)
- `.workflow/TASK-017/*`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `memory-bank/tasks.md`

## Verification performed

```
python -m pytest -q
424 passed in 28.10s

python -m mypy src
Success: no issues found in 82 source files

python -m ruff check src tests
All checks passed!
```

(`tests/contracts/test_scope_guard.py` passes — `docs/spec.md` unchanged this phase.)

## Known gaps

- PolicyGate not yet wired into `engine/orchestrator.py` (skeleton inline policy remains; DEC-028 single-transaction emit is hard acceptance for wiring).
- v1 rate-limit ceiling is fixed until Task 18.
- Production callers must bootstrap WAL via `init_state_dir` before `open_production_state_store`.
- Expired fresh re-issue leaves expired-unrevoked rows in `outstanding_containment_directives` alongside the new row (same idempotency key); duplicate suppression filters by expiry — whether startup step 6/7 should purge these rows is undecided.

## Follow-up tasks

- TASK-018: Transactional rate limits and containment breaker
- Wire PolicyGate into engine intake/edict path (single serializable emit transaction per DEC-028)

## Archive decision

- Accepted

## safe_to_commit

yes
