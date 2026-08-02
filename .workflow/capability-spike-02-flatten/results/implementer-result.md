# Implementer result — capability-spike-02-flatten

## Status

**Complete.** Queue item not marked done (per instructions).

## Changes

| File | Rationale |
|------|-----------|
| `evals/capability/flatten.py` | Generic mechanical flattener: `flatten_event_to_fact`, `resolve_provenance_path`, `SPIKE_UNKNOWN_SOURCE` |
| `tests/evals/capability/test_flatten.py` | 8 tests covering flattening, provenance resolution, host_id, raw_source exclusion, distinct source refs |

## TDD

1. Wrote failing tests first → `ModuleNotFoundError: No module named 'evals.capability.flatten'`
2. Implemented `flatten.py` per plan Task 2
3. All 8 tests pass

## Verification

```
pytest tests/evals/capability/test_flatten.py -q
........                                                                 [100%]
8 passed in 0.32s

ruff check evals/capability/flatten.py tests/evals/capability/test_flatten.py
All checks passed!

mypy evals/capability/flatten.py
Success: no issues found in 1 source file
```

## Commit

`41eae19` — Add generic event flattener for capability spike Path B.

## Constraints observed

- No `src/praetor/` changes
- No harness/scenario changes
- No `praetor.judgment.agentic` imports
- Only allowed files written
- Queue not marked done

## Unresolved

None.
