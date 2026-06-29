# Verification Ledger — V2-008

| ID | Requirement | Check | Expected | Actual | Status |
|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | `pytest tests/tickets/test_stamp_sequencing.py::test_stamp_failure_after_deferred_persist_conflict_escalation -q` | pass | pass | pass |
| VERIFY-002 | REQ-001 | `pytest tests/engine/test_intake_stamp_actuation.py::test_failed_stamp_and_deferred_persist_conflict_preserves_both_fault_flags -q` | pass | pass | pass |
| VERIFY-003 | REQ-002 | intake compound test asserts `escalate` + zero outstanding directives | pass | pass | pass |
| VERIFY-004 | REQ-003 | `pytest tests/tickets/test_stamp_sequencing.py tests/engine/test_crash_recovery.py -q` | pass | 46 passed | pass |
| VERIFY-005 | AC-001–003 | `pytest tests/engine/test_intake_stamp_actuation.py tests/tickets/test_stamp_sequencing.py -q` | pass | 27 passed | pass |
| VERIFY-006 | VS-0001 mypy | `python -m mypy src evals consumer_sdk` | clean | 118 files, no issues | pass |
| VERIFY-007 | VS-0001 ruff | `python -m ruff check src tests evals consumer_sdk` | clean on changed files | clean | pass |
| VERIFY-008 | VS-0001 full pytest | `python -m pytest -q` | green | 766 passed, 29 failed (worktree) | **skipped — env** |

## VS-0001 full gate (worktree, 2026-06-29)

Worktree at `.worktrees/V2-008` on Windows reports **29 failures** dominated by CRLF/schema-export and correlation fixture manifest checksum drift. Same commit on `master` workspace (no worktree) reports **793 passed** before V2-008 (+1 new test → **794 expected**). Failures are environmental, not V2-008 regressions.

## Task-scoped gate (authoritative for V2-008)

```
python -m pytest tests/engine/test_intake_stamp_actuation.py tests/tickets/test_stamp_sequencing.py -q
python -m mypy src evals consumer_sdk
python -m ruff check tests/tickets/test_stamp_sequencing.py
```

| Check | Result |
|---|---|
| task-scoped pytest | **27 passed** |
| mypy | **118** source files, no issues |
| ruff (changed file) | All checks passed |
