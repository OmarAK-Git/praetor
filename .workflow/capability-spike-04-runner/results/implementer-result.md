# Implementer result — capability-spike-04-runner

## Status

**Complete** — all verification commands green.

## Files changed

| File | Rationale |
|------|-----------|
| `evals/capability/runner.py` | `Observation` dataclass, `open_spike_store`, two-path `run_anchor` via `process_alert_intake` (Path A correlation / Path B flattened bundle) |
| `tests/evals/capability/test_runner.py` | Four offline tests with `FakeProvider` covering both paths, fact-count delta, runs repetition, and proposed disposition recording |

## Verification

```
pytest tests/evals/capability/test_runner.py -q
# 4 passed in 0.93s

ruff check evals/capability/runner.py tests/evals/capability/test_runner.py
# All checks passed!

mypy evals/capability/runner.py
# Success: no issues found in 1 source file
```

## Constraints honored

- No `src/praetor/` changes
- No `evals/harness.py` or `evals/scenarios/` changes
- No import from `praetor.judgment.agentic`
- `FakeProvider` only (offline)
- Queue not marked done

## Blockers

None.
