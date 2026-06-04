# Traceability Matrix: TASK-011 (reopened)

| Req | AC | Test/Check | Status |
|-----|-----|------------|--------|
| REQ-001 | AC-001 | `test_revocation_transaction_assigns_sequence_and_outbox` | pass |
| REQ-002 | AC-002 | `test_exporter_writes_rows_in_sequence_order` | pass |
| REQ-003 | AC-003 | `test_record_checksum_verifies_after_write` | pass |
| REQ-004 | AC-004 | `test_export_retry_respects_max_retries` | pass |
| REQ-005 | AC-005 | `test_retry_exhaustion_marks_unhealthy_and_alerts` | pass |
| REQ-006 | AC-006 | `test_oldest_pending_age_from_ledger_commit_at` | pass |
| REQ-007 | AC-007 | `test_startup_recovers_pending_feed_rows` | pass |
| REQ-008 | AC-008 | `test_startup_degraded_when_feed_over_slo` | pass |
| REQ-009 | AC-009 | `test_feed_jsonl_has_no_rotation_machinery` | pass |
| REQ-010 | AC-010 | `test_smoke_benchmark_uses_active_org_config_targets` | pass |
| REQ-011 | AC-011 | `test_checksum_verification_failure_is_hard_unhealthy` | pass |
| REQ-012 | AC-012 | `test_crash_recovery_marks_exported_without_duplicate_jsonl_line` | pass |
| REQ-013 | AC-013 | `test_unhealthy_feed_recovers_when_export_succeeds`, `test_startup_recovers_after_transient_unhealthy` | pass |
| REQ-014 | AC-014 | `test_sequence_gap_marks_unhealthy_and_alerts` | pass |
| REQ-015 | AC-015 | `test_canonical_timestamps_zero_microseconds_and_non_utc_offset` | pass |
| REQ-016 | AC-016 | `test_recovery_rejects_projection_mismatch_with_valid_checksum` | pass |
| REQ-017 | AC-017 | `test_corrupt_feed_prefix_*`, `test_duplicate_*`, `test_out_of_order_*` | pass |
| REQ-018 | AC-018 | `test_missing_feed_file_*`, `test_truncated_feed_*`, `test_startup_marks_unhealthy_when_feed_file_missing_*` | pass |
| REQ-019 | AC-019 | `test_schema_invalid_json_line_marks_unhealthy_not_crash` | pass |

**Counts:** revocation 19 + runtime 4 + benchmarks 2 = **25 focused**; full suite **316**.
