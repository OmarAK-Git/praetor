# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–006 | Identity compliance tests (default suite) | `python -m pytest -q tests/correlation/test_correlator_identity_compliance.py` | pass | 12 passed in 0.69s | pass |
| VERIFY-002 | G1 | Default suite includes compliance tests | `python -m pytest -q` | pass incl. 12 compliance | 666 passed, 1 deselected | pass |
| VERIFY-003 | G2–G5 | Production policy gate paths | policy gate tests in compliance module | pass | host fallback + account gate tests pass | pass |
| VERIFY-004 | All | Static typing | `python -m mypy src evals consumer_sdk` | clean | 110 files OK | pass |
| VERIFY-005 | All | Lint | `python -m ruff check src tests evals consumer_sdk` | clean | All checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live OTRF fixture download | TASK-030 scope | TASK-030 gate adds OTRF scenarios |
