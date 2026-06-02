# Traceability: TASK-008

Map requirements → tasks → code → verification. Update as work proceeds.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Persist before delivery | T-003 | `write_pending_health_alert`, `emit_system_health_alert` | V-003 |
| REQ-002 | JSONL + stdout per-channel status | T-003 | `system_health_delivery_attempts`, `deliver_health_alerts` | V-004 |
| REQ-003 | Failed delivery retryable | T-003 | `deliver_health_alerts` retry path | V-005 |
| REQ-004 | Future channels without migration | T-003 | channel column in delivery table | V-006 |
| REQ-005 | `revocation_feed_unhealthy` supported | T-003 | `SystemHealthAlert` contract + emit | V-007 |
| REQ-006 | Outbox-only (not hash chain) | T-003 | separate SQLite tables | V-008 |
| REQ-007 | `critical_transaction` writes | T-003 | outbox.py | V-009 |
| REQ-008 | No docs changes | T-004 | scope guard | V-002 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: T-001 (workflow), T-004 (verification)
- Code changes with no verification: none planned
