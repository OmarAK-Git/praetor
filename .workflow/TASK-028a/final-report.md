# Final Report: TASK-028a

## Summary

Production intake wires PolicyGate + optional metrics on correlation-aware bundles. Gatekeeper follow-up closes the eval directive regression, defers containment directive durability until after terminal stamp (spec ordering), adds auto-contain stamp-failure coverage, and records metrics only on completed actuation.

## Files changed (initial + follow-up)

### Source

- `src/praetor/engine/orchestrator.py` — `persist_directive=False`; deferred emit in one tx after stamp; metrics after ledger append
- `src/praetor/policy/gate.py` — `persist_directive` flag; `persist_deferred_policy_gate_directive_in_transaction`
- `src/praetor/engine/ids.py`, `skeleton.py` — bundle hashing

### Tests, evals, harness

- `evals/harness.py` — directive DB checks; runner expectation-key guard; unknown/pending stamp backends
- `evals/scenarios/auto_contain_stamp_failed.yaml`
- `tests/engine/test_intake_stamp_actuation.py`
- `tests/evals/test_eval_harness.py` — guard + directive teeth tests
- `tests/metrics/test_orchestrator_metrics.py`
- (prior) tripwire, orchestrator metrics, scenario runner updates

### Workflow / Memory Bank

- `.workflow/TASK-028a/*`
- `memory-bank/{decisions,progress,activeContext}.md`

## Verification

```
python -m pytest -q — 653 passed, 1 deselected
python -m evals.harness — 25/25 PASS
python -m mypy src evals consumer_sdk — 110 files clean
python -m ruff check src tests consumer_sdk evals — clean
```

## Known gaps

See `.workflow/TASK-028a/review.md` (feed lag at intake, recovery downgrade, fault-flag static guard).

## safe_to_commit

yes — full gate re-verified 2026-06-15 (gatekeeper follow-up)
