# Verification Ledger: TASK-011 (reopened)

Recorded from repository root (2026-06-04).

| ID | Requirement | Command | Expected | Actual | Status |
|----|-------------|---------|----------|--------|--------|
| VERIFY-001 | Revocation tests | `pytest -q tests/revocation/` | pass | **19 passed** | pass |
| VERIFY-002 | Startup recovery tests | `pytest -q tests/runtime/test_feed_startup_recovery.py` | pass | **4 passed** | pass |
| VERIFY-003 | Benchmark tests | `pytest -q tests/benchmarks/` | pass | **2 passed** | pass |
| VERIFY-004 | Focused TASK-011 | three commands above | pass | **25 passed** | pass |
| VERIFY-005 | Full suite | `pytest -q` | pass | **316 passed** | pass |
| VERIFY-006 | Types | `mypy src/praetor/revocation` | pass | OK | pass |
| VERIFY-007 | Metadata vs on-disk | `test_missing_feed_file_*`, `test_truncated_feed_*`, `test_startup_marks_unhealthy_when_feed_file_missing_*` | unhealthy | pass | pass |
| VERIFY-008 | Schema-invalid prefix | `test_schema_invalid_json_line_marks_unhealthy_not_crash` | unhealthy, no crash | pass | pass |

## VERIFY-006 command (ruff)

```text
ruff check src/praetor/revocation tests/revocation tests/runtime/test_feed_startup_recovery.py tests/benchmarks benchmarks/smoke_serialized_path.py
```

## Skipped checks

| Check | Reason | Risk |
|-------|--------|------|
| Repo-wide ruff | Pre-existing E501 elsewhere | Low |
| PolicyGate wiring | Task 16 | Expected |

## safe_to_commit

**yes**
