# Traceability: TASK-006

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | One non-terminal attempt per alert | T-003 | `attempts.py` partial unique index | V-001 |
| REQ-002 | Loser re-checks completed edict | T-003 | `attempts.allocate_attempt` | V-002 |
| REQ-003 | Three-tuple completed-edict uniqueness | T-003 | `completed_decisions.py` | V-003 |
| REQ-004 | State transitions | T-003 | `attempts.transition_attempt` | V-004 |
| REQ-005 | Aborted does not block changed input | T-003 | `attempts.allocate_attempt` | V-005 |
| REQ-006 | Manual revocation clears key | T-003 | `store.write_manual_revocation` | V-006 |
| REQ-007 | Automated revocation retains key | T-003 | `store.write_automated_revocation` | V-007 |
| REQ-008 | BEGIN IMMEDIATE critical paths | T-003 | uses `critical_transaction` | V-008 |
| REQ-009 | Single-writer documented | T-003 | `store.py` module docstring | V-009 |
| REQ-010 | No docs edits | T-004 | scope guard | V-010 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- Code changes with no verification: none planned
