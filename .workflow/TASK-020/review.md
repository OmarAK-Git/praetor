# Review: TASK-020

## REVIEW-001 — Lifecycle emit on persist (DEC-034)

PolicyGate persists directives with `status=emitted` via `insert_outstanding_directive_in_transaction`. The evaluation return value captures the emitted directive.

## REVIEW-002 — Revocation consolidation

Automated triggers share `automated_revoke_directive_in_transaction` + `revoke_directives_matching_never_contain`. Manual path uses `manual_revoke_directive_in_transaction`: ledger append, feed row, key clear, and `mark_directive_revoked` in one `critical_transaction` (DEC-034).

## REVIEW-003 — Circular import guard

`build_proposed_directive_in_transaction` lazy-imports `embedded_entries_for_target` and requires `critical_transaction`; live never-contain list is caller-supplied (gate's `refreshed_live`).

## Gatekeeper follow-up (2026-06-11)

| Item | Change |
|---|---|
| Manual revocation ledger | `write_manual_revocation_in_transaction` + `manual_revoke_directive_in_transaction`; chain verify test |
| Mid-export feed floor | seq 1 exported + seq 2 pending → floor 1; fresh DB → floor 0 |
| §9 hash negatives | Tampered entries/hash return False; non-empty embedded round-trip |
| Builder hardening | `require_critical_transaction`; removed in-tx recompute fallback |
| Trigger differentiation | reason assertions + alert count == revoked count |
| Emergency atomicity | `_test_before_conflict_revocation` hook; full rollback on failure |

Verification ledger entries must record numbers actually reproduced by running the command at write time, never projected counts. Stale lifecycle/containment totals (17/25 vs collect-only 15/23) were caught by a post-hoc `pytest --collect-only` audit.

## Known gaps

- Supersession API defined but not exercised by PolicyGate v1 (per contracts §4.2).
- `StateStore.write_manual_revocation` (outer API) still record+feed+key only — Task-6 store tests unchanged; production path uses containment.
- PolicyGate not wired into engine orchestrator intake.
- v1 emitted directives typically embed empty never-contain subset (DEC-035).

## safe_to_commit

yes — 485 passed, mypy clean, ruff clean
