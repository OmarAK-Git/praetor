# Traceability: TASK-008

Map requirements → tasks → code → verification. Update as work proceeds.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Persist before delivery | T-003 | `write_pending_health_alert`, `emit_system_health_alert` | V-003 |
| REQ-002 | JSONL + stdout per-channel status | T-003 | `system_health_delivery_attempts`, `deliver_health_alerts` | V-004 |
| REQ-003 | Failed delivery retryable | T-003 | `deliver_health_alerts` retry path | V-005, V-021 |
| REQ-004 | Future channels without migration | T-003 | channel column in delivery table | V-006 |
| REQ-005 | `revocation_feed_unhealthy` supported | T-003 | `SystemHealthAlert` contract + emit | V-007 |
| REQ-006 | Outbox-only (not hash chain) | T-003 | separate SQLite tables | V-008 |
| REQ-007 | `critical_transaction` writes | T-003 | outbox.py | V-009, V-018 |
| REQ-008 | No docs changes | T-004 | scope guard | V-002 |
| REQ-009 | No test fakes in production | T-005 | `tests/alerts/_fakes.py` | V-012 |
| REQ-010 | Accurate contract surface | T-005 | `health.py` docstring | V-013, DEC-026 |
| REQ-011 | Sink failure taxonomy | T-005 | `_deliver_to_sink` | V-014 |
| REQ-012 | Delivery record guards | T-005 | `record_delivery_attempt` | V-015, V-016 |
| REQ-013 | FK enforcement | T-005 | delivery attempts FK | V-017 |
| REQ-014 | Task 9 tx boundary | T-005 | nested critical tx rejection | V-018 |
| REQ-015 | Duplicate alert_id contract | T-005 | idempotent persist | V-019, V-020, DEC-027 |
| REQ-016 | At-least-once JSONL | T-005 | module doc + test | V-022 |
| REQ-017 | Retry query correctness | T-005 | `fetch_retryable_delivery_attempts` | V-023 |
| REQ-018 | Import-order safety | T-005 | lazy store imports | V-024, DEC-025 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: T-001 (workflow), T-004 (verification)
- Code changes with no verification: none
