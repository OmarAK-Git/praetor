# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-032 | `detections/sigma/windows/*.yml` | `test_sigma_rules_parse_without_errors` | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-002 | TASK-032 | pySigma validators | `test_sigma_rules_validate_without_blocking_issues` | REVIEW-001 | pass |
| REQ-003 | AC-003 | — | TASK-032 | `detections/attack_mapping.yaml` | `test_attack_mapping_*`, `test_sigma_rules_have_attack_tags` | REVIEW-001 | pass |
| REQ-004 | AC-004 | DEC-003, DEC-004 | TASK-032 | rule detections | `test_each_fixture_event_matches_at_least_one_rule` | REVIEW-001 | pass |
| REQ-005 | AC-005 | — | TASK-032 | `detections/` tree | file presence + VERIFY-001 | REVIEW-001 | pass |
