# Final Report: TASK-030

## Summary

Implemented the correlation accuracy gate: manifest checksum verification runs before correlation, human-authored expected YAML scenarios assert required event collection and process relationships, and in-window noise overcollection is bounded by configurable thresholds.

## Files changed

### Eval gate

- `evals/correlation_gate.py` — manifest verification, scenario loader, gate runner, CLI
- `evals/correlation_expected/otrf_process_chain_corroborated_logon.yaml` — pass scenario (excludes out-of-window noise)
- `evals/correlation_expected/otrf_noisy_in_window_bounded.yaml` — bounded in-window noise scenario

### Tests

- `tests/evals/test_correlation_gate.py` — **12** gate tests (pass, fail, manifest block, CLI)

### Workflow / Memory Bank

- `.workflow/TASK-030/*`
- `memory-bank/{tasks,activeContext,progress}.md`

## Verification

```
python -m pytest -q tests/evals/test_correlation_gate.py — 12 passed
python -m pytest -q — 678 passed, 1 deselected
python -m mypy src evals consumer_sdk — 111 files clean
python -m ruff check src tests evals consumer_sdk — clean
python -m evals.correlation_gate — 2 scenarios PASS
```

## Known gaps

See `.workflow/TASK-030/review.md` (bulk OTRF download deferred to Task 31).

## safe_to_commit

yes — verification green 2026-06-15
