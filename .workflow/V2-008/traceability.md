# Traceability Matrix — V2-008

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-053 | T-001,T-002 | `orchestrator.py` conflict handler | `test_stamp_failure_after_deferred_persist_conflict_escalation`, `test_failed_stamp_and_deferred_persist_conflict_preserves_both_fault_flags` | REVIEW-001 | complete |
| REQ-002 | AC-002 | DEC-053 | T-003 | orchestrator in-band escalate rebuild | intake compound test directive count + disposition | REVIEW-001 | complete |
| REQ-003 | AC-003 | PE-0021, PE-0025 | T-001 | `tickets/contract.py` (unchanged) | `test_stamp_sequencing.py`, `test_crash_recovery.py` stamp-failed tests | REVIEW-001 | complete |
