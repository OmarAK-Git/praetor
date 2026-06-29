# Traceability Matrix — V2-012

| Req | AC | Decision | Task | Code/Diff | Test/Check | Status |
|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-058 | T-001 | `org_config_sections.py` | `test_default_action_round_trips_in_snapshot` | pass |
| REQ-002 | AC-002 | DEC-058 | T-002 | `preflight.py` | `test_missing_default_action_fails_preflight`, `test_invalid_default_action_fails_preflight` | pass |
| REQ-003 | AC-003 | DEC-058 | T-003 | `containment_policy.py` | `test_scoped_allow_overrides_default_escalate`, `test_asset_group_allow_overrides_default_escalate` | pass |
| REQ-004 | AC-004 | DEC-058 | T-003 | `containment_policy.py` | `test_default_action_applies_when_no_rule_matches` | pass |
| REQ-005 | AC-005 | DEC-058 | T-004 | `example_org.yaml` | `EXAMPLE_SNAPSHOT_HASH` pin in `tests/config/shared.py` | pass |
