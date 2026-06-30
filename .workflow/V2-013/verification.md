# Verification Ledger — V2-013

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Policy unit tests | `pytest tests/policy/test_containment_policy.py -q` | pass | pass | pass |
| VERIFY-002 | REQ-004 | Gate regression | `pytest tests/policy/test_policy_gate.py::test_no_matching_rule_escalates_at_gate -q` | pass | pass | pass |
| VERIFY-003 | REQ-005 | Full suite | `python -m pytest -q` | pass | 836 passed, 2 deselected, 1 xfailed | pass |
| VERIFY-004 | REQ-005 | Static checks | `mypy src evals consumer_sdk`; `ruff check src tests evals consumer_sdk` | clean | clean | pass |
| VERIFY-005 | REQ-002 | Eval harness | `python -m evals.harness` | all pass | 31/31 PASS | pass |
| VERIFY-006 | REQ-005 | Phase 3 gate | `python -m evals.run_phase3_gate` | pass | all checks PASS | pass |
| VERIFY-007 | REQ-002 | Walkthrough | `nbconvert --execute` + `check_walkthrough.py` | OK | OK | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| `docs/operator_runbook.md` | Hard limit: no docs/ edits | low — gap in review.md |
