# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | plan.md Task 26 + matrix completeness | T-002 | `evals/scenarios/*.yaml` (24) | `test_outcome_matrix_completeness_guard` | REVIEW-002 | complete |
| REQ-002 | AC-001 | contracts.md §13 Outcome Matrix | T-002 | `evals/outcome_matrix.py`, `evals/harness.py` | `test_scenario_sfe_polarity_matches_canonical_map` | REVIEW-002 | complete |
| REQ-003 | AC-001 | contracts.md §13 degraded-mode note | T-002 | `revocation_feed_unhealthy_blocks_autocontain.yaml` | harness + completeness guard | REVIEW-002 | complete |
| REQ-004 | AC-001 | spec.md account/never-contain rows | T-002 | account + never-contain scenarios | policy_gate runner | REVIEW-002 | complete |
| REQ-005 | AC-001 | plan.md prompt_construction_isolation | T-002 | `prompt_construction_isolation.yaml` | harness prompt_isolation runner | REVIEW-002 | complete |
| REQ-006 | AC-001 | plan.md non-zero exit | T-002 | `evals/harness.py:main` | `test_harness_main_exits_zero_on_success` | REVIEW-002 | complete |
| REQ-007 | Follow-up | OutcomeMatrixFaultFlag enum SSOT | T-004 | `evals/outcome_matrix.py` | `test_scenario_fault_flags_are_canonical_enum_values` | REVIEW-002 | complete |
| REQ-008 | Follow-up | ticket_stamp_failed §13 row | T-004 | `ticket_stamp_failed.yaml` | `test_ticket_stamp_failed_scenario_present` | REVIEW-002 | complete |
| REQ-009 | Follow-up | policy_gate idempotency | T-004 | `policy_gate_idempotency.yaml` | harness idempotency_suppressed_on_repeat | REVIEW-002 | complete |
