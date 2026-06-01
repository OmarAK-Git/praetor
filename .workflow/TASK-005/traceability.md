# Traceability: TASK-005

Map requirements → tasks → code → verification. Update as work proceeds.

| Req ID | Requirement (summary) | Task ID | Code / artifact | Verification |
|--------|-------------------------|---------|-----------------|--------------|
| REQ-001 | Singleton lock acquisition failure exits non-zero | T-003 | `runtime/singleton.py` `SingletonLock.acquire` | V-001, V-002 |
| REQ-002 | Non-WAL journal mode rejected at startup | T-003 | `state/sqlite_guard.py` `verify_journal_mode` | V-003 |
| REQ-003 | Connection isolation explicit | T-003 | `state/sqlite_guard.py` `create_guarded_connection` | V-004 |
| REQ-004 | BEGIN IMMEDIATE on critical paths | T-003 | `state/sqlite_guard.py` `critical_transaction` | V-005, V-006 |
| REQ-005 | Lock held for process lifetime | T-003 | `runtime/singleton.py` `SingletonLock` | V-007 |
| REQ-006 | Second process blocked on same state dir | T-003 | `runtime/singleton.py` | V-008 |
| REQ-007 | No docs modifications | T-004 | scope guard | V-009 |

## Orphan / unmapped

- Requirements with no task: none
- Tasks with no requirement: none
- Code changes with no verification: none
