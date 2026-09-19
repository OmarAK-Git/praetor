# Implementer result — eval-kernel-07-gov-recovery

## Summary

Implemented Task 7 (`gov.recovery_never_contains`) per `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md`.

## Files changed

| File | Rationale |
|---|---|
| `evals/e2e_scenarios/gov.recovery_never_contains.yaml` | Locked governance scenario: STAMP_RESOLVED auto_contain candidate recovered via startup recovery must escalate, never contain. |
| `evals/e2e_kernel.py` | Added `_run_gov_recovery` using `run_engine_startup_recovery` / recovery resolver seed pattern; dispatched in `run_e2e_scenario`. |
| `tests/evals/e2e/test_gov_recovery_never_contains.py` | E2E pin test asserting both arms pass with expected recovery dispositions and no containment directive. |

## Verification

```
pytest tests/evals/e2e/test_gov_recovery_never_contains.py -q
# 1 passed in 3.72s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_recovery_never_contains.py
# All checks passed!

mypy evals/e2e_kernel.py
# Success: no issues found in 1 source file
```

## Commit

```
feat(evals): pin gov.recovery_never_contains on startup recovery
```

Pushed to `eval-kernel-sprint1`.

## Notes

- Uses `run_engine_startup_recovery` with `SucceedingStampBackend`, not PolicyGate-only.
- Queue **not** marked done (per packet).
