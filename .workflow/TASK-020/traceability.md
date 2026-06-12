# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-034: emit on persist | T-001 | `containment/lifecycle.py` | `test_status_transitions_proposed_to_emitted` | REVIEW-001 | complete |
| REQ-002 | AC-001 | contract validator | T-001 | `contracts/containment.py` | `test_directive_lifetime_capped_at_300_seconds` | REVIEW-001 | complete |
| REQ-003 | AC-001 | SID pattern | T-001 | `contracts/containment.py` | `test_account_target_id_must_be_sid` | REVIEW-001 | complete |
| REQ-004 | AC-001 | §9 embedded subset | T-001 | `containment/lifecycle.py` | `test_embedded_hash_matches_live_never_contain_hash` | REVIEW-001 | complete |
| REQ-005 | AC-001 | verified-export floor | T-001 | `revocation/outbox.py` | `test_minimum_feed_sequence_uses_verified_export` | REVIEW-001 | complete |
| REQ-006 | AC-001 | consumer verify helper | T-001 | `containment/lifecycle.py` | `test_consumer_verifies_embedded_hash` | REVIEW-001 | complete |
| REQ-007 | AC-002 | ledger + feed | T-002 | `containment/revocation.py` | `test_automated_revocation_writes_ledger_and_feed` | REVIEW-002 | complete |
| REQ-008 | AC-002 | never_contain_conflict | T-002 | `containment/revocation.py` | `test_post_emission_conflict_emits_alert_keeps_key` | REVIEW-002 | complete |
| REQ-009 | AC-002 | manual path + ledger (DEC-034) | T-002 | `containment/revocation.py`, `state/store.py` | `test_manual_revocation_clears_key_in_one_tx` | REVIEW-002 | complete |
| REQ-010 | AC-002 | supersession fields | T-002 | `containment/revocation.py` | `test_supersession_includes_superseded_by_keeps_key` | REVIEW-002 | complete |
| REQ-011 | AC-002 | post-activation | T-002 | `containment/revocation.py` | `test_post_activation_reconciliation_revokes_and_alerts` | REVIEW-002 | complete |
| REQ-005 | AC-001 | mid-export feed floor | T-004 | `test_minimum_feed_sequence_excludes_pending_unexported` | VERIFY-007 | REVIEW-004 | complete |
| REQ-006 | AC-001 | §9 negatives + non-empty | T-004 | hash tamper + round-trip tests | VERIFY-001 | REVIEW-004 | complete |
| REQ-* | AC-003 | regression + emergency atomicity | T-004 | full suite | VERIFY-003, VERIFY-008 | REVIEW-003 | complete |
