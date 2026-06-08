# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001..REQ-008 | Task 13 scoped tests | `python -m pytest -q tests/judgment/test_provider_failures.py` | pass | 10 passed | passed |
| VERIFY-002 | REQ-001, REQ-003..REQ-006 | Engine regression tests | `python -m pytest -q tests/engine/` | pass | 26 passed | passed |
| VERIFY-003 | REQ-001..REQ-008 | Full test suite | `python -m pytest -q` | pass | 354 passed | passed |
| VERIFY-004 | REQ-001, REQ-008 | Static typing | `python -m mypy src` | pass | Success: no issues found in 70 source files | passed |
| VERIFY-005 | REQ-001..REQ-008 | Lint | `python -m ruff check src tests` | pass | All checks passed | passed |

## TDD Red Checks

| ID | Test | Command/Evidence | Expected Failure | Actual | Status |
|---|---|---|---|---|---|
| RED-001 | Provider failure tests before implementation | `python -m pytest -q tests/judgment/test_provider_failures.py` | fail because `praetor.judgment` provider layer is missing | Failed with `ModuleNotFoundError: No module named 'praetor.judgment'` | passed |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Real Vertex/Gemini integration | Task 13 only requires a stub; real provider adversarial probe is Task 27. | Stub API may need refinement when real integration starts. |
