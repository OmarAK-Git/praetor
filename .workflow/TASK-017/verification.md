# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–014 | PolicyGate tests | `python -m pytest -q tests/policy/` | pass | 28 passed | pass |
| VERIFY-002 | REQ-015 | Policy + crash recovery | `python -m pytest -q tests/policy tests/engine/test_crash_recovery.py` | pass | 48 passed | pass |
| VERIFY-003 | All | Full regression | `python -m pytest -q` | pass | 424 passed | pass |
| VERIFY-004 | All | Mypy | `python -m mypy src` | clean | 82 files clean | pass |
| VERIFY-005 | All | Ruff | `python -m ruff check src tests` | clean | all checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Engine orchestrator PolicyGate wiring | Out of TASK-017 file list; gate module tested in isolation | Medium until intake calls `evaluate_policy_gate` |
