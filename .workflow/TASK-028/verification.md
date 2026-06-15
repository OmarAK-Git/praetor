# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–007 | Correlation unit tests | `python -m pytest -q tests/correlation/test_sysmon_normalization.py` | pass | 9 passed in 0.21s | pass |
| VERIFY-002 | REQ-008 | Fixture manifest smoke | `python -m pytest -q tests/test_smoke.py::test_fixture_manifest_loads` | pass | included in full suite | pass |
| VERIFY-003 | All | Full suite regression | `python -m pytest -q` | pass | 638 passed, 1 deselected, 3 xfailed | pass |
| VERIFY-004 | All | Static typing | `python -m mypy src evals consumer_sdk` | clean | 110 files OK | pass |
| VERIFY-005 | All | Lint | `python -m ruff check src tests consumer_sdk evals` | clean | All checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live OTRF fixture download | Task 29 scope; v1 uses committed minimal fixtures | Task 30 gate will add OTRF scenarios |
