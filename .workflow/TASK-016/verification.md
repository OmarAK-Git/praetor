# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–006 | Account corroboration unit tests | `python -m pytest -q tests/evidence/test_account_corroboration.py` | pass | 20 passed | pass |
| VERIFY-002 | REQ-001–006 | Red before green | pre-implementation `ModuleNotFoundError: praetor.evidence.provenance` | fail | confirmed | pass |
| VERIFY-003 | All | Full suite regression | `python -m pytest -q` | pass | 395 passed | pass |
| VERIFY-004 | All | Type check | `python -m mypy src` | pass | success, 77 source files | pass |
| VERIFY-005 | All | Lint | `python -m ruff check src tests` | pass | all checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Engine integration | Out of scope until TASK-017 PolicyGate | Eligibility not yet wired to intake |
