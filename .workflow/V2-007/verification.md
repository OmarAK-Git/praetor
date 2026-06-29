# Verification Ledger — V2-007

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VS-0001 | All | Scoped pytest | `python -m pytest tests/engine/ tests/metrics/ tests/judgment/test_provider_failures.py tests/judgment/test_provider_health_breaker.py tests/evals/test_provider_unavailable_matrix.py tests/evals/test_eval_harness.py -q` | pass | **161 passed** | pass |
| VS-0002 | All | Types | `python -m mypy src evals consumer_sdk` | clean | 118 files, no issues | pass |
| VS-0003 | All | Lint | `python -m ruff check src tests evals consumer_sdk` | clean | All checks passed | pass |
| VS-0004 | REQ-001–002 | Engine intake | `tests/engine/test_provider_unavailable_intake.py` | 2 passed | 2 passed | pass |
| VS-0005 | REQ-004 | Metrics | `test_intake_records_provider_unavailable_llm_failure_metric` | pass | pass | pass |
| VS-0006 | REQ-001 | Harness | `python -m evals.harness --scenario provider_unavailable` | PASS | PASS | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Full `pytest -q` (797 tests) | V2-005 base has 30 pre-existing failures without V2-006 policy test fixes | low for V2-007 scope |
