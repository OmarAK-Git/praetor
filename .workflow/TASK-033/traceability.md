# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001, DEC-004 | TASK-002 | `tools/compile_sigma.py`, `detections/spl/*.spl` | `test_committed_spl_matches_compiler`, VERIFY-002 | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-002 | TASK-002 | `validate_rule_supported` | `test_unsupported_modifier_raises_clear_error` | REVIEW-001 | pass |
| REQ-003 | AC-003 | DEC-001 | TASK-002 | `splunk/savedsearches.conf` | `test_savedsearches_conf_*` | REVIEW-001 | pass |
| REQ-004 | AC-004 | DEC-003 | TASK-002 | `tools/splunk_ingest_demo.ps1` | `test_ingest_script_validate_only`, tamper test | REVIEW-001 | pass |
| REQ-005 | AC-005 | DEC-003 | TASK-002 | `splunk/README.md` | integration marker + VERIFY-003 | REVIEW-001 | pass |
