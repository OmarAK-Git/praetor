# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | DEC-052 | Citation-anchored targeting | `tests/policy/test_citation_anchored_host_targeting.py` | 5 passed | 5 passed | pass |
| VERIFY-002 | DEC-052 | Multi-host matrix scenario | `python -m evals.harness` incl. `multi_host_target_ambiguity` | pass | 25/25 PASS | pass |
| VERIFY-003 | REQ-002 | Window exclusion 9999 | `test_window_excludes_out_of_window_record_9999` | pass | pass | pass |
| VERIFY-004 | REQ-002 | Healthy noisy gate | `test_noisy_correlation_gate_passes_on_healthy_tree` | pass | pass | pass |
| VERIFY-005 | Phase 3 CLI | `python -m evals.run_phase3_gate --skip-identity-subprocess` | exit 0 | exit 0 | pass |
| VERIFY-006 | Correlation CLI | `python -m evals.correlation_gate` | 5/5 PASS | 5/5 PASS | pass |
| VERIFY-007 | Full suite | `pytest -q` | pass | 705 passed, 1 xfailed | pass |
| VERIFY-008 | Types | `mypy src evals consumer_sdk` | clean | 112 files OK | pass |
| VERIFY-009 | Lint | `ruff check src tests evals consumer_sdk` | clean | clean | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| External OTRF bulk dataset | Deferred per TASK-030 | Low |
| REQ-001 TASK-028a intake in phase 3 CLI | Policy gate path only | Medium |
| Cross-host correlator drop | strict xfail forward pressure (REVIEW-004) | Low |
