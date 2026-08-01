# Implementer result — fix anchor_time (capability-spike-04-runner)

## Status

**Complete** — blocking review finding fixed; all verification commands green.

## Root cause

Path A called `process_alert_intake` without `anchor_time`, so the orchestrator defaulted to `datetime.now(UTC)`. Historical fixture events (2026-01-01) fell outside the ±300s correlation window → empty bundle → `correlation_failure` → FakeProvider never consulted.

## Files changed

| File | Rationale |
|------|-----------|
| `evals/capability/runner.py` | Pass `anchor_time=anchor.anchor_time` in `intake_kwargs` for both Path A and Path B |
| `tests/evals/capability/test_runner.py` | Add `test_path_a_correlates_in_window_events` asserting no `correlation_failure` and proposed disposition matches FakeProvider |

## Verification

```
pytest tests/evals/capability/test_runner.py -q
# 5 passed in 1.09s

ruff check evals/capability/runner.py tests/evals/capability/test_runner.py
# All checks passed!

mypy evals/capability/runner.py
# Success: no issues found in 1 source file
```

## Constraints honored

- No `src/praetor/` changes
- No harness changes
- Queue not marked done

## Blockers

None.
