# Traceability: TASK-003

Map requirements → tasks → code → verification.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Single canonical serialization | T-003 | `hashing/canonical.py` | V-001, V-014 |
| REQ-002 | UTF-8, key sort, RFC3339 timestamps | T-003 | `canonical.py` | V-002, V-003, V-004 |
| REQ-003 | Reject NaN/Infinity, unknown fields | T-003 | `canonical.py` | V-005, V-006 |
| REQ-004 | Absent vs null distinct | T-003 | `canonical.py` | V-007 |
| REQ-005 | Length-delimited concatenation | T-003 | `canonical.py` | V-008 |
| REQ-006 | Domain constants module-only | T-003 | `hashing/domains.py` | V-009, V-015 |
| REQ-007 | `decision_id` construction | T-003 | `domains.py` | V-010 |
| REQ-008 | Idempotency key construction | T-003 | `domains.py` | V-011 |
| REQ-009 | `EMPTY_BUNDLE` sentinel | T-003 | `canonical.py` | V-012 |
| REQ-010 | Feed record checksum | T-003 | `domains.py` | V-013 |
| REQ-011 | Never-contain entries hash | T-003 | `domains.py` | V-016 |
| REQ-012 | `stamp_id` domain + delimited hash | T-003 | `domains.py` | V-017 |
| REQ-013 | No inline domain literals | T-004 | repo grep | V-015 |
| REQ-014 | Stable repeated hashes | T-003 | tests | V-001 |
| REQ-015 | No `docs/` changes | T-005 | git diff guard | V-018 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- Code changes with no verification: none (pending implementation)
