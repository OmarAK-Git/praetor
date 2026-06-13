# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-035 | T-001 | `consumer_sdk/reference_verifier.py` | `test_expired_directive_non_actionable` | REVIEW-001 | complete |
| REQ-002 | AC-001 | DEC-010 | T-001 | `consumer_sdk/reference_verifier.py` | `test_revoked_directive_non_actionable` | REVIEW-001 | complete |
| REQ-003 | AC-001 | §9 | T-001 | `consumer_sdk/reference_verifier.py` | `test_embedded_hash_mismatch_escalates` | REVIEW-001 | complete |
| REQ-004 | AC-001 | §8.3 | T-001 | `consumer_sdk/reference_verifier.py` | `test_feed_cursor_below_floor_escalates` | REVIEW-001 | complete |
| REQ-005 | AC-001 | §10.3 | T-001 | `consumer_sdk/reference_verifier.py` | `test_feed_stale_escalates` | REVIEW-001 | complete |
| REQ-006 | AC-001 | DEC-038 | T-001 | `consumer_sdk/reference_verifier.py` | `test_sequence_gap_escalates`, `test_truncated_window_starting_above_one_passes` | REVIEW-001 | complete |
| REQ-007 | AC-001 | §11 | T-001 | `consumer_sdk/reference_verifier.py` | `test_clock_sync_uncertainty_escalates` | REVIEW-001 | complete |
| REQ-008 | AC-001 | §10.5 | T-001 | `consumer_sdk/reference_verifier.py` | `test_lineage_conflict_escalates` | REVIEW-001 | complete |
| REQ-009 | AC-001 | §10 | T-001 | `consumer_sdk/reference_verifier.py` | `test_valid_directive_actionable` | REVIEW-001 | complete |
| REQ-010 | AC-001 | plan | T-001 | `consumer_sdk/reference_verifier.py` | `test_result_includes_required_fields` | REVIEW-001 | complete |
| REQ-001–010 | AC-002 | — | T-003 | — | VERIFY-001–009 | REVIEW-002 | complete |
