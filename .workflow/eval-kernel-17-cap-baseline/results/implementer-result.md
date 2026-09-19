# Implementer result — eval-kernel-17-cap-baseline

## Summary

Implemented Task 17 (`cap.baseline_bag_path_a`): Path A bag via `correlate_telemetry` (Sysmon EventID 1 + Security 4624) fed into `process_alert_intake`. No Path B.

## Files changed

| File | Rationale |
|---|---|
| `evals/e2e_scenarios/cap.baseline_bag_path_a.yaml` | Locked scenario YAML with bag-path pins and `stipulated_capability` theater detector |
| `evals/e2e_kernel.py` | Added `_run_cap_baseline` executor, wired dispatch, excluded bag-path pass from `scorecard_is_quality_pass` |
| `tests/evals/e2e/test_cap_baseline_bag_path_a.py` | E2E pin test: `old_build=pass`, `new_build=pending` |

## Behavior

- **old_build**: `status=pass` when bag-path pins match (EventIDs `[1, 4624]`, correlate + intake ran, no Path B).
- **new_build**: forced to `status=pending`, `failure_class=none` via existing `CAPABILITY_QUALITY_IDS` logic.
- **Theater**: `_quality_pass_forbidden` returns `False` for this ID so bag-path `pass` is not scored as a FakeProvider capability quality pass (`stipulated_capability` stays clean).
- **Label leak**: `frozen_label: malicious` is metadata only; not placed in `alert_identity`.

## Verification

```text
$ pytest tests/evals/e2e/test_cap_baseline_bag_path_a.py tests/evals/test_scorecard.py -q
.......                                                                  [100%]
7 passed in 4.25s

$ ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_baseline_bag_path_a.py
All checks passed!

$ mypy evals/e2e_kernel.py
Success: no issues found in 1 source file
```

## Unresolved

- None. Queue status not updated per task instructions.
