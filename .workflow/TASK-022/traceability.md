# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-039 | T-001 | `engine/timeouts.py` | `test_provider_latency_beyond_sla_escalates`, `test_slow_auto_contain_proposal_latency_sla_blocks_containment`, cumulative-retry tests | REVIEW-001 | complete |
| REQ-002 | AC-001 | DEC-040 | T-002 | `engine/queue_policy.py` | `test_aged_non_terminal_recovery_emits_queue_aging`, `test_queue_aging_exceeded_boundary` | REVIEW-001 | complete |
| REQ-003 | AC-001 | Outcome Matrix | T-003 | `engine/orchestrator.py` | outcome matrix assertions | REVIEW-001 | complete |
| REQ-004 | AC-001 | DEC-040 | T-003 | `engine/recovery.py` | recovery + stamp-precedence tests | REVIEW-001 | complete |
| REQ-005 | AC-001 | — | T-001–T-002 | `engine/timeouts.py`, `engine/queue_policy.py` | `test_latency_and_queue_fault_flags_are_distinct` | REVIEW-001 | complete |
| REQ-001–005 | AC-002 | — | T-004 | — | VERIFY-001–009 | REVIEW-002 | complete |
