# Implementer result — eval-kernel-18-cap-stump

## Summary

Implemented Task 18 (`cap.stump_parity_guard`): path_a_fact_count stump with McNemar-ready pairs, `quality_win_claimed` pinned false, `old_build` pass, `new_build` pending.

## Files changed

| File | Rationale |
|---|---|
| `evals/stump.py` | `path_a_fact_count_stump` + `stump_pair` (McNemar-ready keys, never claims quality win) |
| `evals/e2e_scenarios/cap.stump_parity_guard.yaml` | Locked scenario YAML with same Path A bag as Task 17 |
| `evals/e2e_kernel.py` | `_run_cap_stump_parity_guard` executor; exempt scenario from stipulated_capability false positive on old_build pass |
| `tests/evals/test_stump.py` | Stump threshold + McNemar-ready pair unit tests |
| `tests/evals/e2e/test_cap_stump_parity_guard.py` | E2E pin: no quality win, old pass / new pending |

## Verification

```
pytest tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py -q
→ 3 passed in 4.75s

ruff check evals/stump.py evals/e2e_kernel.py tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py
→ All checks passed!

mypy evals/stump.py evals/e2e_kernel.py
→ Success: no issues found in 2 source files
```

## Constraints honored

- `quality_win_claimed` is always `False` in observed output
- `new_build` status is `pending`, not `pass`
- McNemar-ready pair keys: `stump_prediction`, `stump_correct`, `model_bucket`, `model_correct`
- No judgment-beats-stump claim

## Unresolved

None.
