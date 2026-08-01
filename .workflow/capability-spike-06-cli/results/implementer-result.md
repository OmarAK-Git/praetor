# Implementer result — capability-spike-06-cli

## Summary

Added offline-safe capability spike CLI (`evals/capability_spike.py`) with tests and non-gating documentation.

## Files changed

| File | Rationale |
|------|-----------|
| `evals/capability_spike.py` | CLI entry point: env-gated provider resolution, JSONL capture loader, anchor runner orchestration, A/B summary |
| `tests/evals/capability/test_cli.py` | TDD tests for offline default, provider gating, capture loading, harness isolation |
| `docs/eval_gates.md` | Appended non-gating section per plan Task 6 |

## Implementation note

`main()` checks `resolve_spike_provider()` **before** `argparse.parse_args()` so `main()` can be called without argv under pytest (sys.argv contains pytest args). Behavior unchanged for `python -m evals.capability_spike` offline skip path.

## Verification

```
python -m pytest tests/evals/capability/test_cli.py -q
# 6 passed in 0.38s

ruff check evals/capability_spike.py tests/evals/capability/test_cli.py
# All checks passed!

mypy evals/capability_spike.py
# Success: no issues found in 1 source file

python -m evals.capability_spike
# capability spike skipped: PRAETOR_CAPABILITY_SPIKE not enabled
# exit 0
```

## Constraints honored

- No `src/praetor/**` changes
- No `evals/harness.py` or `evals/scenarios/**` changes
- Never imports `praetor.judgment.agentic`
- Offline-safe default (exit 0 skip without env + key)
- Not imported by harness (verified by test)
- Queue not marked done

## Commit

`Add capability spike CLI with offline-safe default.`
