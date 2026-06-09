# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001: Reuse shared citation validator | T-003 | `policy/gate.py` | `test_invalid_citation_escalates` | REVIEW-001 | complete |
| REQ-002 | AC-001 | DEC-002: Snapshot never-contain from org binding | T-002 | `policy/containment_policy.py` | `test_snapshot_never_contain_escalates` | REVIEW-001 | complete |
| REQ-003 | AC-001 | DEC-003: Live never-contain includes emergencies | T-003 | `policy/gate.py` | `test_live_emergency_never_contain_escalates` | REVIEW-001 | complete |
| REQ-004 | AC-001 | DEC-004: Return live entries on evaluation | T-003 | `policy/gate.py` | `test_emergency_entry_embedded_in_directive` | REVIEW-001 | complete |
| REQ-005 | AC-001 | DEC-005: Account signals block host fallback; `target is None` → ambiguous | T-002/T-003 | `containment_policy.py`, `gate.py` | `test_insufficient_account_corroboration_escalates`, `test_sid_without_corroboration_escalates_without_host_fallback` | REVIEW-006 | complete |
| REQ-006 | AC-001 | DEC-006: Feature gate constant | T-003 | `policy/identity.py` | `test_account_containment_disabled_when_gate_false` | REVIEW-001 | complete |
| REQ-007 | AC-001 | DEC-007: Synthetic tests bypass activation preflight | T-004 | `tests/policy/conftest.py` | `test_account_auto_contain_when_feature_gate_enabled` | REVIEW-001 | complete |
| REQ-008 | AC-002 | DEC-008: Target-scoped rules only at gate | T-002 | `policy/containment_policy.py` | `test_policy_ambiguity_escalates` | REVIEW-002 | complete |
| REQ-009 | AC-001 | DEC-009: Fixed v1 scope limit until Task 18 | T-001 | `policy/state.py` | `test_rate_limit_exceeded_escalates` | REVIEW-003 | complete |
| REQ-010 | AC-001 | DEC-010: Check outstanding before rate limit | T-003 | `policy/gate.py` | `test_duplicate_idempotency_key_suppresses_emission` | REVIEW-001 | complete |
| REQ-011 | AC-001 | DEC-011: Expired re-issue is fresh (same key, no supersession) | T-003 | `policy/gate.py` | `test_expired_directive_allows_fresh_reissue` | REVIEW-008 | complete |
| REQ-012 | AC-001 | DEC-012: Reuse feed actuation probe | T-003 | `policy/gate.py` | `test_feed_unhealthy_blocks_auto_contain` | REVIEW-001 | complete |
| REQ-013 | AC-001 | DEC-013: Single critical_transaction for emit path | T-003 | `policy/gate.py` | `test_auto_contain_mutations_occur_in_one_transaction` | REVIEW-001 | complete |
| REQ-014 | AC-001 | DEC-014: PolicyGateResult shape | T-003 | `policy/gate.py` | `test_proposed_and_final_dispositions_recorded_separately` | REVIEW-001 | complete |
| REQ-015 | AC-003 | DEC-015: Reconcile idempotency + reset rate counters | T-001 | `engine/recovery.py` | `test_policy_state_recovery.py` | REVIEW-004 | complete |
| REQ-016 | AC-004 | DEC-016: `open_production_state_store` wrapper | T-004 | `runtime/startup.py` | production entrypoint tests | REVIEW-005 | complete |
