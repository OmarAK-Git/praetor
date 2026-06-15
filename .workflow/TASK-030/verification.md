# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Known scenario gate pass | `pytest tests/evals/test_correlation_gate.py -k known_otrf` | pass | 1 passed | pass |
| VERIFY-002 | REQ-002 | Noise threshold pass/fail | `pytest tests/evals/test_correlation_gate.py -k noise` | pass | 2 passed | pass |
| VERIFY-003 | REQ-003 | Missing relationship fail | `pytest tests/evals/test_correlation_gate.py -k relationship` | pass | 1 passed | pass |
| VERIFY-004 | REQ-004 | Manifest checksum gate | `pytest tests/evals/test_correlation_gate.py -k manifest` | pass | 3 passed | pass |
| VERIFY-005 | REQ-005 | Gate module CLI | `python -m evals.correlation_gate` | exit 0 | exit 0, 2 scenarios PASS | pass |
| VERIFY-006 | REQ-005 | Full test suite | `python -m pytest -q` | all pass | 678 passed, 1 deselected | pass |
| VERIFY-007 | REQ-005 | Static analysis | `python -m mypy src evals consumer_sdk` | clean | 111 files clean | pass |
| VERIFY-008 | REQ-005 | Lint | `python -m ruff check src tests evals consumer_sdk` | clean | clean (after --fix) | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live OTRF/Mordor download | Out of scope; committed fixtures per DEC-001 | Task 31 may add larger fixture set |
