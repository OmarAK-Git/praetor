# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-029: limit=1/scope/window | T-001 | `policy/rate_limit.py` | `test_per_host_limit_*`, `test_per_subnet_*`, `test_sliding_window_resets_host_limit_after_window` | REVIEW-001 | complete |
| REQ-001 | AC-001 | DEC-030: per_asset_group collapses to host asset_id | T-001 | `policy/rate_limit.py` | `test_per_asset_group_scope_collapses_to_per_host_for_v1` | REVIEW-001 | complete |
| REQ-002 | AC-001 | registry-only subnet/group | T-001 | `policy/rate_limit.py` | `test_unregistered_host_only_checks_per_host_scope` | REVIEW-001 | complete |
| REQ-003 | AC-001 | in-tx re-check + committed failure record | T-003 | `policy/gate.py` `_RateLimitRaceLoss` | `test_in_tx_rate_limit_race_loser_records_single_failure` | REVIEW-002 | complete |
| REQ-003 | AC-001 | pre-check path no double-count | T-003 | `policy/gate.py` | `test_pre_check_rate_limit_failure_not_double_counted` | REVIEW-002 | complete |
| REQ-004 | AC-002 | sliding window failures trip breaker | T-002 | `policy/circuit_breaker.py` | `test_sliding_window_failures_trip_containment_breaker` | REVIEW-003 | complete |
| REQ-005 | AC-002 | containment_breaker_open alert + emit schema | T-002,T-003 | `health_emit.py`, `gate.py` | `test_breaker_trip_emits_health_alert`, `test_gate_breaker_trip_without_preinitialized_outbox` | REVIEW-003 | complete |
| REQ-006 | AC-002 | skip counter updates when open | T-001,T-003 | `policy/rate_limit.py`, `gate.py` | `test_rate_counters_unchanged_while_breaker_open` | REVIEW-003 | complete |
| REQ-007 | AC-002 | success_reset_threshold resets failure tally (closed); DEC-031: window-elapse recovery (open) | T-002 | `policy/circuit_breaker.py` | `test_success_reset_threshold_clears_failure_state`, `test_breaker_recovers_after_window_elapses` | REVIEW-003 | complete |
