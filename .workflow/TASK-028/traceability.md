# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-002 | TASK-002 | `src/praetor/correlation/sysmon.py` | `test_sysmon_process_creation_normalizes` | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-002 | TASK-002 | `src/praetor/correlation/security_log.py` | `test_security_logon_normalizes` | REVIEW-002 | pass |
| REQ-003 | AC-003 | DEC-001 | TASK-002 | `sysmon.py`, `security_log.py` | `test_every_fact_has_raw_source` | REVIEW-003 | pass |
| REQ-004 | AC-004 | DEC-003 | TASK-002 | `src/praetor/correlation/excerpts.py` | `test_prompt_excerpt_set_is_bounded_and_raw_source_free` | REVIEW-004 | pass |
| REQ-005 | AC-005 | DEC-002 | TASK-002 | `src/praetor/correlation/entities.py` | `test_parent_child_process_relationships` | REVIEW-005 | pass |
| REQ-006 | AC-006 | DEC-004 | TASK-002 | `src/praetor/correlation/window.py` | `test_time_window_excludes_noise` | REVIEW-006 | pass |
| REQ-007 | AC-007 | DEC-005 | TASK-002 | `src/praetor/correlation/sysmon.py` | `test_ambiguous_user_sets_ambiguity_flag` | REVIEW-007 | pass |
| REQ-008 | AC-008 | — | TASK-003 | `tests/fixtures/fixture_manifest.yaml` | `test_fixture_manifest_registers_checksums` | REVIEW-008 | pass |
