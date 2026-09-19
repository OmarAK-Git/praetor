# Implementer result — eval-kernel-12-thr-wrong-process

## Summary

Implemented Task 12 (`thr.valid_cite_wrong_process`) per Sprint 1 plan. Citations resolve to the parent process fact but omit the subject Path A child process; the harness records `cite_to_subject: false` without implementing Sprint 2 McNemar.

## Files changed

| File | Rationale |
|---|---|
| `evals/e2e_scenarios/thr.valid_cite_wrong_process.yaml` | Locked scenario YAML with sysmon/security fixtures, subject/cite GUIDs, and scorecard pins |
| `evals/e2e_kernel.py` | Added `_load_fixture_events`, `_run_thr_wrong_process`, and dispatch branch; imports `REPO_ROOT` from harness |
| `tests/evals/e2e/test_thr_valid_cite_wrong_process.py` | Pin test asserting both arms pass with citations valid but cite-to-subject miss |

## Verification

```
pytest tests/evals/e2e/test_thr_valid_cite_wrong_process.py -q
.                                                                        [100%]
1 passed in 2.46s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_valid_cite_wrong_process.py
All checks passed!

mypy evals/e2e_kernel.py
Success: no issues found in 1 source file
```

## Commit

```
088477a feat(evals): pin thr.valid_cite_wrong_process cite-to-subject miss
```

Pushed to `origin/eval-kernel-sprint1`.

## Unresolved

None. Queue not marked done per instructions.
