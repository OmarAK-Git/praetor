# Traceability: TASK-004

Map requirements → tasks → code → verification.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Three external write surfaces | T-003 | `auth/verifier.py` `WriteSurface` | V-001 |
| REQ-002 | Org-config activation → `soc_lead` | T-003 | `authenticate_org_config_activation` | V-002, V-003 |
| REQ-003 | Emergency never-contain → `soc_lead` | T-003 | `authenticate_emergency_never_contain` | V-004, V-005 |
| REQ-004 | Annotation → `analyst` | T-003 | `authenticate_annotation_submission` | V-006, V-007 |
| REQ-005 | Wrong role rejected | T-002 | tests | V-003, V-005, V-007 |
| REQ-006 | Missing token rejected | T-002 | tests | V-008 |
| REQ-007 | Verified principal identity | T-003 | `Principal.identity`, `verified_record_identity` | V-009, V-010 |
| REQ-008 | Internal ops not external | T-003 | `guard_internal_only`, `authenticate_external_write` | V-011, V-012 |
| REQ-009 | Pluggable verifier; issuance OOS | T-003 | `TokenVerifier` protocol | V-013 |
| REQ-010 | No `docs/` changes | T-005 | git diff guard | V-014 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- Code changes with no verification: pending implementation
