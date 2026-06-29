# Verification Ledger — V2-006

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Sole escalate unit test | `pytest tests/policy/test_containment_policy.py -q` | pass | 7 passed | pass |
| VERIFY-002 | REQ-002 | Distinct deny/escalate | same | pass | pass | pass |
| VERIFY-003 | REQ-003 | Policy ambiguity conflict | `test_policy_gate.py::test_policy_ambiguity_escalates` | pass | pass | pass |
| VERIFY-004 | REQ-004 | Gate deny/escalate mapping | `test_sole_escalate_rule_blocks_auto_contain`, `test_sole_deny_rule_blocks_auto_contain` | pass | pass | pass |
| VERIFY-005 | All | VS-0001 full gate | `python -m pytest -q` | all pass | **799 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-006 | All | mypy | `python -m mypy src evals consumer_sdk` | clean | 118 files, no issues | pass |
| VERIFY-007 | All | ruff | `python -m ruff check src tests evals consumer_sdk` | clean | All checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| — | — | — |
