# Verification Ledger — V2-010

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–004 | V2-010 tests | `python -m pytest -q tests/engine/test_recovery_policy_pinning.py tests/engine/test_crash_recovery.py tests/policy/test_policy_state_recovery.py` | pass | **29 passed** | pass |
| VERIFY-002 | REQ-001–004 | Scoped suites | `python -m pytest -q tests/engine tests/policy tests/containment tests/runtime tests/ledger tests/state tests/alerts` | pass | **247 passed** | pass |
| VERIFY-003 | All | mypy | `python -m mypy src evals consumer_sdk` | clean | 118 files, no issues | pass |
| VERIFY-004 | All | ruff | `python -m ruff check src tests evals consumer_sdk` | clean | all passed | pass |
| VERIFY-005 | Regression | Full gate | `python -m pytest -q` | pass | 770 passed, 30 failed (env) | skip |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Full `pytest -q` green | 30 failures on V2-005 base worktree: Windows CRLF `schemas/*.json` export drift + correlation fixture manifest checksum mismatches — same class of failures absent on main at V2-006 WIP (797/799 pass) | Low for V2-010 scope; failures unrelated to recovery changes |
| `docs/operator_runbook.md` update | Task hard limit: no `docs/` edits | Runbook orphan alert code not documented until doc task |
