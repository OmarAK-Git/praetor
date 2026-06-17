# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Codification unit tests | `python -m pytest -q tests/codification/test_sweep.py` | 17 pass | 17 passed | pass |
| VERIFY-002 | REQ-002 | Preflight rejection | `test_proposed_artifact_rejected_by_preflight` | `proposed_artifact_not_activatable` | pass | pass |
| VERIFY-003 | REQ-003–005 | Report content | `test_report_documents_*`, `test_sweep_exposes_reviewable_*` | limits + risks | pass | pass |
| VERIFY-004 | all | Full suite | `python -m pytest -q` | pass | 778 passed, 2 deselected, 1 xfailed | pass |
| VERIFY-005 | all | Static analysis | `python -m mypy src evals consumer_sdk` | clean | 118 files clean | pass |
| VERIFY-006 | all | Lint | `python -m ruff check src tests evals consumer_sdk` | clean | All checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live SOC review | Human gate outside CI | Expected — artifact is for operator review |
