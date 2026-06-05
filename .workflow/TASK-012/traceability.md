# Traceability Matrix: TASK-012

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-012 | `engine/orchestrator.py` happy path | `test_hardcoded_bundle_produces_valid_decision_edict` (VERIFY-001) | DEC-001 | pass |
| REQ-002 | AC-002 | DEC-002 | TASK-012 | single-site EMPTY_BUNDLE in `engine/ids.py` | `test_correlation_failure_*`, `test_stored_bundle_hash_equals_decision_id_input` (VERIFY-003) | DEC-006 | pass |
| REQ-003 | AC-003 | DEC-003 | TASK-012 | budget gate before judgment provider | `test_config_over_budget_*` (VERIFY-001) | DEC-001 | pass |
| REQ-004 | AC-004 | DEC-004 | TASK-012 | citation validator | `test_invalid_citation_escalates` (VERIFY-001) | DEC-004 | pass |
| REQ-005 | AC-005 | DEC-005 | TASK-012 | `engine/recovery.py` (steps 4,5,7) | `test_crash_*`, `test_unknown_stamp_*`, `test_failed_stamp_*`, `test_crash_window_*` (VERIFY-002) | DEC-005, DEC-007 | pass |
| REQ-006 | AC-006 | DEC-006 | TASK-012 | directive never-contain scan + ledger + health alert | `test_startup_scans_*`, `test_startup_directive_scan_is_idempotent` (VERIFY-002) | DEC-008 | pass |
| REQ-007 | AC-007 | DEC-007 | TASK-012 | stamp payload on edict | `test_ticket_stamp_payload_present_on_happy_path` (VERIFY-001) | DEC-001 | pass |

REVIEW IDs map to decisions in `review.md` (DEC-001..DEC-008).
