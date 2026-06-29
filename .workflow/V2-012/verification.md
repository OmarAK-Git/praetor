# Verification Ledger — V2-012

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–002 | Config tests | `python -m pytest -q tests/config` | pass | 58 passed | pass |
| VERIFY-002 | REQ-003–004 | Policy tests | `python -m pytest -q tests/policy/test_containment_policy.py` | pass | 10 passed | pass |
| VERIFY-003 | REQ-001–005 scoped | Config + policy | `python -m pytest -q tests/config tests/policy` | pass | 127 passed | pass |
| VERIFY-004 | Full gate VS-0001 | Suite + static | `pytest -q`, `mypy`, `ruff` | green | 835 passed, 2 deselected, 1 xfailed; mypy 118 clean; ruff clean | pass |
| VERIFY-005 | Eval harness | Scenario runner | `python -m evals.harness` | pass | all mandatory scenarios green | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Walkthrough / notebook CI | V2-013 scope | low — notebook still references legacy ref string |
