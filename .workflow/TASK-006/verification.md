# Verification: TASK-006

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | At most one non-terminal attempt per `alert_identity` | second allocate fails | `test_at_most_one_non_terminal_per_alert` | pass |
| V-002 | Duplicate intake loser re-checks completed edict | no fresh attempt after winner completes | `test_loser_rechecks_*`, `test_active_holder_rechecks_*` | pass |
| V-003 | Completed-edict uniqueness on three-tuple | duplicate tuple returns same completed row | `test_completed_tuple_*`, `test_three_tuple_uniqueness_*` | pass |
| V-004 | Attempt state transitions | FSM enforced; invalid transitions rejected | `test_happy_path_*`, `test_invalid_transition_*` | pass |
| V-005 | Aborted attempt allows new tuple on same alert | new attempt allocated | `test_aborted_allows_changed_input_retry` | pass |
| V-006 | Manual revocation: record + feed outbox + key cleared | one transaction | `test_manual_revocation_*` | pass |
| V-007 | Automated revocation: record + feed outbox; key retained | one transaction | `test_automated_revocation_*` | pass |
| V-008 | Allocation/revocation use `critical_transaction` | scope guard + no bare BEGIN in state | existing scope guard | pass |
| V-009 | Single-writer constraint documented | module docstring | `test_store_module_documents_single_writer` | pass |
| V-010 | No `docs/` modifications | scope guard | git diff docs/ empty | pass |
| V-011 | Full `pytest -q` | all pass | 132 passed in 1.85s | pass |
| V-012 | `mypy src` | no errors | 31 files pass | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 — `pytest -q`, `mypy src`
- **Overall:** pass

## Gaps / skipped checks

- Hash-chain ledger append for revocations (Task 10)
- Feed JSONL export and startup recovery (Tasks 11–12)
- Full PRAGMA list from absent `docs/operator_runbook.md` (Task 35)
- Concurrent threading race test skipped — serialized re-check tests cover intake-race rule
