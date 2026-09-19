# Implementer result — eval-kernel-14-use-ledger

## Status
**Done** — Task 14 implemented per plan.

## Changes

| File | Rationale |
|---|---|
| `evals/e2e_scenarios/use.reconstruct_from_ledger.yaml` | Usability scenario YAML with ledger reconstruction pins |
| `evals/e2e_kernel.py` | Added `_run_use_reconstruct` executor and dispatch branch |
| `tests/evals/e2e/test_use_reconstruct_from_ledger.py` | TDD pin test for both arms |

## Behavior

After `process_alert_intake`, the executor fetches ledger rows, validates the latest `decision_edict` record as `DecisionEdict`, and compares `decision_id`, `evidence_bundle_hash`, and `final_disposition` against the intake edict. Missing ledger edicts or mismatches surface as harness failures via scorecard pin comparison or exception rows.

## Verification (fresh)

```
pytest tests/evals/e2e/test_use_reconstruct_from_ledger.py -q
# 1 passed in 3.40s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_reconstruct_from_ledger.py
# All checks passed!

mypy evals/e2e_kernel.py
# Success: no issues found in 1 source file
```

## TDD

1. Wrote failing test — failed with missing YAML / only old_build error row.
2. Added YAML + `_run_use_reconstruct` — test passes.

## Commit

`feat(evals): pin use.reconstruct_from_ledger from ledger rows`

## Unresolved

None. Queue not marked done per packet instructions.
