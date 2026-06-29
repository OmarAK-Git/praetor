# Traceability Matrix — V2-010

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-060, PE-0007 | T-003 | `engine/recovery.py` `_recovery_disposition_for_stamp` | `test_recovery_disposition_*`, `test_failed_stamp_with_autocontain_*` | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-060 § orphans | T-001, T-002 | `policy/state.py`, `recovery.py`, `revocation.py` | `test_orphan_directive_emits_health_alert` | REVIEW-002 | pass |
| REQ-003 | AC-003 | DEC-060, AG-0045 | T-001 | `reconcile_policy_state` (unchanged skip) | `test_reconcile_skips_idempotency_when_ledger_edict_missing` | REVIEW-003 | pass |
| REQ-004 | AC-004 | spec § startup | T-003 | `state/store.py` (unchanged order) | `test_reopen_store_exports_feed_after_directive_reconciliation` | REVIEW-004 | pass |
