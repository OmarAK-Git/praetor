# Implementer Result — V2-015 Gate Target Ownership Guard

## Files Changed

- `src/praetor/policy/gate.py` — added `resolved_target` on `PolicyGateEvaluation`; added `gate_resolved_containment_target()` helper with directive consistency checks; set `resolved_target` on auto_contain evaluation returns.
- `src/praetor/engine/orchestrator.py` — intake persist path uses `gate_resolved_containment_target(gate_evaluation)` instead of rebuilding `ContainmentTarget` from directive fields; removed unused `ContainmentTarget` import.
- `tests/engine/test_gate_target_ownership.py` — static AST guard, helper rejection test, two-host intake integration proving uncited WORKSTATION2 cannot steer persisted target, corroboration negative path, happy-path persist assertion.

## Gate Target Ownership

PolicyGate now exposes the evaluated containment target on `PolicyGateEvaluation.resolved_target`. Intake calls `gate_resolved_containment_target()` before `persist_deferred_policy_gate_directive_in_transaction`, enforcing AG-0080: orchestrator cannot re-derive targets from bundle facts.

## Verification

```
pytest tests/engine/ tests/policy/ -q
124 passed in 15.83s
```

Retry after verifier AC3 gap: added `test_intake_two_host_bundle_persists_only_cited_gate_target`.

```
pytest tests/engine/ tests/policy/ -q
125 passed
```

## Approval Gates

None hit.
