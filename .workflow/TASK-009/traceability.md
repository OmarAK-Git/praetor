# Traceability Matrix: TASK-009 (third reopen)

| Req | AC | Task | Code/Diff | Test/Check | Status |
|-----|-----|------|-----------|------------|--------|
| REQ-001 | Stable snapshot hash | T-004 | `config/snapshot.py`, `loader.py` | `test_valid_config_loads_stable_snapshot_hash` | pass |
| REQ-002 | Preflight validations | T-004 | `config/preflight.py` | `test_org_config_loader.py`, `test_config_gate.py` | pass |
| REQ-003 | In-flight snapshot binding | T-004 | `config/activation.py`, `state.py` | `test_in_flight_attempt_*` | pass |
| REQ-004 | Post-activation reconciliation | T-004 | `config/activation.py` | `test_post_activation_reconciliation_*` | pass |
| REQ-005 | Emergency + conflict revocations | T-004 | `config/emergency.py` | `test_emergency_*.py` | pass |
| REQ-006 | Expiry / no authorize contain | T-004 | `config/emergency.py` | `test_expired_*`, `test_emergency_cannot_authorize` | pass |
| REQ-007 | soc_lead auth | T-004 | `auth/verifier.py` | `test_wrong_role_rejected` | pass |
| REQ-008 | Contracts §3a updates | T-004 | `docs/contracts.md` §3a | hash vector + verbatim render rows | pass (docs updated in-task) |
| REQ-009 | Strict policy integers | T-004 | `preflight.py`, `org_config_sections.py` | `test_directive_lifetime_string_*`, `test_probe_rate_*` | pass |
| REQ-010 | PreflightError on binding serialize | T-004 | `config/snapshot.py` | `test_business_context_float_invalid_binding_value` | pass |
| REQ-011 | Fetch verifies JSON snapshot_hash | T-004 | `config/state.py` | `test_stored_snapshot_hash_field_mismatch_*` | pass |
| REQ-012 | Multi-verbatim per hash | T-004 | `org_config_verbatim_renders` | `test_same_binding_hash_stores_multiple_verbatim_renders` | pass |
| REQ-013 | Health flush recovery | T-004 | `health_emit.py`, activation/emergency | `test_activation_drains_unflushed_*`, `test_health_flush_retries_*` | pass |
