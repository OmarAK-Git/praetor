# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | AC-001 | Latency/queue tests | `python -m pytest -q tests/engine/test_latency_and_queue_aging.py` | pass | 14 passed | pass |
| VERIFY-002 | AC-002 | Full regression | `python -m pytest -q` | pass | 523 passed in 37.64s | pass |
| VERIFY-003 | AC-002 | Type check | `python -m mypy src consumer_sdk` | clean | 92 files OK | pass |
| VERIFY-004 | AC-002 | Lint | `python -m ruff check src tests consumer_sdk` | clean | All checks passed | pass |
| VERIFY-005 | GK-001 | Slow AUTO_CONTAIN blocked | `test_slow_auto_contain_proposal_latency_sla_blocks_containment` | pass | pass | pass |
| VERIFY-006 | GK-002 | Cumulative-retry latency | `test_cumulative_retry_latency_includes_backoff_and_attempts`, `test_cumulative_retry_latency_under_sla_when_total_time_ok` | pass | pass | pass |
| VERIFY-007 | GK-003 | Intake queue-aging removed | orchestrator has no queue-aging check; DEC-040 | pass | pass | pass |
| VERIFY-008 | GK-004 | Stamp-path precedence | `test_aged_pending_stamp_resolves_via_stamp_not_queue_aging`, `test_aged_stamp_resolved_completes_without_queue_aging` | pass | pass | pass |
| VERIFY-009 | GK-005 | Queue boundary symmetry | `test_queue_aging_exceeded_boundary` | pass | pass | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| `docs/contracts.md` provider SLA field | start-task hard limit | v1 uses DEC-039 module constant |
