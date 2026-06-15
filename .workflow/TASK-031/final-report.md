# Final Report: TASK-031

## Summary

Implemented the Phase 3 regression gate: requires human-authored `noisy_correlated_real_telemetry.yaml`, runs correlation accuracy on noisy OTRF-style fixtures, verifies identity compliance tests and account containment preflight prerequisites, and asserts Phase 2 safety invariants on Task 28 correlated bundle output (account gate-off + host path on noisy sysmon-only subset).

## Files changed

### Phase 3 gate

- `evals/run_phase3_gate.py` — gate orchestrator, correlated bundle helper, CLI
- `evals/correlation_expected/noisy_correlated_real_telemetry.yaml` — noisy real telemetry expected output

### Tests

- `tests/evals/test_phase3_regression_gate.py` — **9** gate tests

### Workflow / Memory Bank

- `.workflow/TASK-031/*`
- `memory-bank/{tasks,activeContext,progress}.md`

## Verification

```
python -m pytest -q tests/evals/test_phase3_regression_gate.py — 9 passed
python -m pytest -q tests/evals/test_correlation_gate.py — 19 passed
python -m pytest -q — 694 passed, 1 deselected
python -m mypy src evals consumer_sdk — 112 files clean
python -m ruff check src tests evals consumer_sdk — clean
python -m evals.correlation_gate — 5 scenarios PASS
python -m evals.run_phase3_gate --skip-identity-subprocess — all checks PASS (incl. phase2_harness)
```

## Known gaps

See `.workflow/TASK-031/review.md` (bulk OTRF download deferred).

## safe_to_commit

yes — verification green 2026-06-15
