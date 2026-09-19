# Implementer result — eval-kernel-08-des-envelope

## Task
Task 8: `des.envelope_rejects_extra_fields` from `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md`

## Changes

| File | Rationale |
|------|-----------|
| `evals/e2e_scenarios/des.envelope_rejects_extra_fields.yaml` | Scenario definition pinning extra-field rejection on both arms |
| `evals/e2e_kernel.py` | Added `_run_des_envelope` executor and wired it in `run_e2e_scenario` |
| `tests/evals/e2e/test_des_envelope_rejects_extra_fields.py` | E2E test asserting both arms pass with expected pins |

## TDD evidence

1. **Red:** `pytest tests/evals/e2e/test_des_envelope_rejects_extra_fields.py -v` → FAIL (missing YAML / no executor; only placeholder `old_build` row)
2. **Green:** After YAML + executor → PASS

## Verification

```
pytest tests/evals/e2e/test_des_envelope_rejects_extra_fields.py -q
# 1 passed in 1.77s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_envelope_rejects_extra_fields.py
# All checks passed!

mypy evals/e2e_kernel.py
# Success: no issues found in 1 source file
```

## Commit

`feat(evals): pin des.envelope_rejects_extra_fields against CBC expansion` — pushed to `eval-kernel-sprint1`.

## Notes

- Did not modify `src/praetor/contracts/alert.py` (ContractModel `extra="forbid"` already enforces rejection).
- Did not mark queue item done (per packet instructions).
