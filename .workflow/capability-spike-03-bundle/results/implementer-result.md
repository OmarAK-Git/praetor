# Implementer result — capability-spike-03-bundle

## Status

Done. Queue item not marked done (per instructions).

## Changes

| File | Rationale |
|------|-----------|
| `evals/capability/bundle.py` | Path B `build_spike_bundle` reusing `filter_events_in_window` and `filter_events_to_anchor_host` from `praetor.correlation`, then flattening all event types via Task 2 helpers |
| `tests/evals/capability/test_bundle.py` | Six TDD tests: rejected event types included, window/host filtering, provenance paths, empty input, undatable skip |

## Design notes

- `_datable` drops events before windowing when `event_timestamp` raises `ValueError` or `TypeError`.
- Flatten failures are skipped per-event (same exception types).
- No `src/praetor` edits; no harness/scenarios/agentic touched.

## Verification

```
pytest tests/evals/capability/test_bundle.py -q
→ 6 passed in 0.32s

ruff check evals/capability/bundle.py tests/evals/capability/test_bundle.py
→ All checks passed!

mypy evals/capability/bundle.py
→ Success: no issues found in 1 source file
```

## Commit

`Add Path B bundle builder reusing correlation window and host filters.`

## Unresolved

None.
