# Traceability Matrix — V2-003

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-060 § snapshot | T-001, T-002 | `docs/contracts.md` §7a | `rg "DEC-060" docs/` | REVIEW-007 | complete |
| REQ-002 | AC-002 | DEC-060 § expired re-issue | T-001, T-002 | `docs/contracts.md` §4.2 | `test_expired_directive_allows_fresh_reissue` | REVIEW-008 | complete |
| REQ-003 | AC-003 | DEC-060 § expired rows | T-001, T-002 | `docs/contracts.md` §4.2.1 | `fetch_outstanding_unrevoked_directives` expiry filter | — | complete |
| REQ-004 | AC-004 | DEC-060 § orphans | T-001, T-002 | `docs/contracts.md` §4.2.1 | `test_reconcile_skips_idempotency_when_ledger_edict_missing` | AG-0045 | complete |
