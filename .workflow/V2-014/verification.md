# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Host isolation unit tests | `python -m pytest -q tests/correlation/test_host_isolation.py` | pass | 5 passed | pass |
| VERIFY-002 | REQ-001 | Cross-host xfail removed | `python -m pytest -q tests/evals/test_phase3_regression_gate.py::test_correlator_should_drop_cross_host_in_window_noise` | pass | 1 passed | pass |
| VERIFY-003 | REQ-002 | Correlation gate | `python -m pytest -q tests/evals/test_correlation_gate.py` | pass | 18 passed | pass |
| VERIFY-004 | REQ-004 | Citation targeting | `python -m pytest -q tests/policy/test_citation_anchored_host_targeting.py` | pass | 5 passed | pass |
| VERIFY-005 | REQ-005 | Phase 3 gate | `python -m evals.run_phase3_gate --skip-harness --skip-identity-subprocess` | exit 0 | all PASS | pass |
| VERIFY-006 | REQ-005 | Full suite | `python -m pytest -q` | pass | 842 passed, 2 deselected | pass |
| VERIFY-007 | REQ-005 | Static analysis | `python -m mypy src evals consumer_sdk` + ruff | clean | clean | pass |
| VERIFY-008 | REQ-005 | Eval harness | `python -m evals.harness` | 31/31 PASS | 31/31 PASS | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| `docs/` update | Hard limit: do not modify docs | AG-0080 playbook entry stale until dream consolidate |
