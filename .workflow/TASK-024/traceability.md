# Traceability Matrix: TASK-024

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | — | TASK-024 | `metrics/collector.py` `record_disposition` | `test_disposition_distribution_increments` | REVIEW-001 | pass |
| REQ-002 | AC-001 | — | TASK-024 | `record_policy_gate_result` | `test_policy_gate_override_rate_increments` | REVIEW-001 | pass |
| REQ-003 | AC-001 | — | TASK-024 | `record_llm_failure` | `test_llm_failure_metric_increments_per_fault_flag` | REVIEW-001 | pass |
| REQ-004 | AC-001 | — | TASK-024 | `record_containment_directive` | `test_containment_directive_count_increments` | REVIEW-001 | pass |
| REQ-005 | AC-001 | — | TASK-024 | `record_queue_aging_fallback` | `test_queue_aging_fallback_increments` | REVIEW-001 | pass |
| REQ-006 | AC-001 | — | TASK-024 | `record_breaker_state` | `test_provider_and_containment_breaker_state_metrics_independent` | REVIEW-001 | pass |
| REQ-007 | AC-001 | — | TASK-024 | `record_probe_outcome` / `record_production_call_outcome` | `test_probe_outcome_metrics_independent_from_production_call_metrics` | REVIEW-001 | pass |
| REQ-008 | AC-001 | — | TASK-024 | `record_probe_rate_limited` | `test_probe_rate_limit_metric_tracks_probe_rate_limit_per_minute` | REVIEW-001 | pass |
| REQ-009 | AC-001 | — | TASK-024 | `record_stamp_status` | `test_stamp_status_metric_increments` | REVIEW-001 | pass |
| REQ-010 | AC-001 | — | TASK-024 | `record_health_alert_delivery` | `test_health_alert_delivery_status_metric_increments` | REVIEW-001 | pass |
| REQ-011 | AC-001 | — | TASK-024 | `record_feed_export_lag` | `test_feed_export_lag_recorded_per_record` | REVIEW-001 | pass |
| REQ-012 | AC-001 | — | TASK-024 | `MetricsSnapshot.feed_export_lag_p99_seconds` | `test_p99_feed_export_lag_and_warning_threshold_metric_exist` | REVIEW-001 | pass |
| REQ-013 | AC-001 | — | TASK-024 | `record_revocation_feed_unhealthy_transition` | `test_revocation_feed_unhealthy_transition_metric_increments` | REVIEW-001 | pass |
| — | AC-002 | — | TASK-024 | scope guard | `test_only_expected_top_level_packages` | REVIEW-001 | pass |
