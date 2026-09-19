# Implementer result — eval-kernel-09-des-path-b

## Task
Task 9: `des.path_b_stays_out_of_src` from `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md`

## Changes

| File | Rationale |
|------|-----------|
| `evals/e2e_scenarios/des.path_b_stays_out_of_src.yaml` | Scenario definition pinning `path_b_import_found: false` on both arms |
| `evals/e2e_kernel.py` | Added `_run_des_path_b` executor (AST/import guard via `path_b_in_src` theater detector) and wired it in `run_e2e_scenario` |
| `tests/evals/e2e/test_des_path_b_stays_out_of_src.py` | E2E test + static AST guard that kernel does not import `evals.capability.flatten` |

## TDD evidence

1. **Red:** `pytest tests/evals/e2e/test_des_path_b_stays_out_of_src.py -v` → FAIL (missing YAML / no executor; only placeholder `old_build` row)
2. **Green:** After YAML + executor → PASS (2 passed)

## Verification

```
pytest tests/evals/e2e/test_des_path_b_stays_out_of_src.py -q
# 2 passed in 2.47s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_path_b_stays_out_of_src.py
# All checks passed!

mypy evals/e2e_kernel.py
# Success: no issues found in 1 source file
```

## Commit

`feat(evals): pin des.path_b_stays_out_of_src import guard` — pushed to `eval-kernel-sprint1` (`f9e918e`).

## Notes

- Did not modify `src/praetor/` (Path B stays out of production source).
- Kernel module has no `evals.capability.flatten` import (verified by AST test).
- Did not mark queue item done (per packet instructions).
