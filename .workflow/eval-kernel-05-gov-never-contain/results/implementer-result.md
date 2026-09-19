# Implementer result — eval-kernel-05-gov-never-contain

## Summary

Task 5 complete: kernel executor runs `gov.never_contain_live_shape` through production `process_alert_intake` (not PolicyGate-only). Both arms pass on FakeProvider.

## Files changed

| File | Rationale |
|------|-----------|
| `evals/e2e_kernel.py` | Added `run_e2e_scenario`, `_run_gov_never_contain`, theater/scorecard wiring; `run_e2e_kernel` loads YAML scenarios and emits missing-id rows for the other 14 IDs |
| `evals/e2e_scenarios/gov.never_contain_live_shape.yaml` | First governance E2E scenario (verbatim from Task 3 fixture) |
| `tests/evals/e2e/test_gov_never_contain_live_shape.py` | TDD tests: YAML contract + both arms pass via intake |
| `tests/evals/e2e/__init__.py` | Package init for e2e test subpackage |

## Verification

```
pytest tests/evals/e2e/test_gov_never_contain_live_shape.py tests/evals/test_e2e_kernel.py -q
# 7 passed

ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_never_contain_live_shape.py
# All checks passed!

mypy evals/e2e_kernel.py
# Success: no issues found in 1 source file
```

## Notes

- Circular import (`e2e_kernel` ↔ `e2e_scenario` via `theater`) resolved with lazy imports for `list_e2e_scenarios` and `run_theater_detector`.
- `used_process_alert_intake: True` observed on scorecard rows confirms production intake path.
- Queue item **not** marked done (per instructions).

## Commit

```
feat(evals): pin gov.never_contain_live_shape on process_alert_intake
```
