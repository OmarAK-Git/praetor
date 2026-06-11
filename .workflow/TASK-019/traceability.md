# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | — | TASK-019 | `provider_health_breaker.record_provider_production_failure_in_transaction` | `test_provider_failures_trip_breaker` | REVIEW-001 | pass |
| REQ-002 | AC-002 | — | TASK-019 | `PROVIDER_HEALTH_BREAKER_ALERT_CODE` | `test_breaker_trip_emits_distinct_health_alert` | REVIEW-001 | pass |
| REQ-003 | AC-003 | DEC-028 | TASK-019 | `gate.is_breaker_open(PROVIDER_HEALTH)` | `test_production_escalates_while_breaker_open` | REVIEW-001 | pass |
| REQ-004 | AC-004 | — | TASK-019 | `trigger_half_open_probes_by_soc_lead` | `test_soc_lead_trigger_enters_half_open` | REVIEW-001 | pass |
| REQ-005 | AC-005 | — | TASK-019 | `maybe_enter_half_open_from_timer` | `test_timer_enters_half_open` | REVIEW-001 | pass |
| REQ-006 | AC-006 | — | TASK-019 | `PROVIDER_HEALTH_CANARY_PAYLOAD` | `test_probe_uses_canary_only` | REVIEW-001 | pass |
| REQ-007 | AC-007 | — | TASK-019 | `_probe_rate_limit_exceeded` | `test_probe_rate_limited` | REVIEW-001 | pass |
| REQ-008 | AC-008 | — | TASK-019 | `provider_health_metrics` table | `test_probe_metrics_independent_from_production` | REVIEW-001 | pass |
| REQ-009 | AC-009 | — | TASK-019 | `_record_probe_failure` | `test_probe_failure_reopens_breaker` | REVIEW-001 | pass |
| REQ-010 | AC-010 | — | TASK-019 | probe success path | `test_consecutive_probe_successes_close_breaker` | REVIEW-001 | pass |
| REQ-011 | AC-011 | — | TASK-019 | separate `BreakerDomain` rows | `test_breaker_domains_independent` | REVIEW-001 | pass |
| REQ-012 | AC-012 | — | TASK-019 | `provider_failure_trips_breaker` | `test_provider_unavailable_trips_breaker` | REVIEW-001 | pass |
