# Traceability: TASK-007

Map requirements → tasks → code → verification. Update as work proceeds.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Pending before external call | T-003 | `stamp.py` `execute_stamp`, `outbox.py` `write_pending_stamp` | V-003 |
| REQ-002 | Durable success/failure | T-003 | `outbox.py` `record_stamp_outcome` | V-004 |
| REQ-003 | Timeout → `unknown` | T-003 | `stamp.py` timeout handling | V-005 |
| REQ-004 | Recovery same `stamp_id` | T-003 | `stamp.py` `execute_stamp` recovery path | V-006 |
| REQ-005 | Idempotent fake backend | T-002/T-003 | `tests/tickets/test_stamp_outbox.py`, backend protocol | V-007 |
| REQ-006 | Non-idempotent risk documented | T-003 | `stamp.py` module doc / constant | V-008 |
| REQ-007 | `unknown` ≠ `failed` | T-003 | `StampStatus` enum | V-009 |
| REQ-008 | `critical_transaction` for writes | T-003 | `outbox.py` | V-010 |
| REQ-009 | No docs changes | — | scope guard | V-002 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- Code changes with no verification: store.py schema init hook → covered by V-001
