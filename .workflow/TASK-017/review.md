# Review

## REVIEW-001 — PolicyGate outcome paths

PolicyGate enforces citation validation, never-contain snapshot/live, account identity, feature gate, feed health, idempotency, and rate-limit checks before emitting `auto_contain`. Fault flags align with Outcome Matrix rows tested in `test_policy_gate.py`.

## REVIEW-002 — Target-scoped policy ambiguity

Gate-time evaluation considers only explicitly scoped containment rules; global `default_escalate` does not create false ambiguity when the model proposes `auto_contain`.

## REVIEW-003 — Rate limit v1 ceiling

Task 17 uses a fixed per-scope counter limit (`_V1_DEFAULT_SCOPE_LIMIT = 1`) with persisted counters. Task 18 should replace this with org-config sliding windows and subnet/asset-group scopes.

## REVIEW-004 — Startup step 6

`reconcile_policy_state` registers idempotency keys for outstanding directives and resets rate counters on startup. Breaker state persists across restart; full breaker reconciliation semantics remain with Task 18/19.

## REVIEW-005 — Production entrypoint

`open_production_state_store` fails closed without a held singleton lock. Callers must still invoke `init_state_dir` before first production open (documented gap for Task 35 runbook).

## REVIEW-006 — Account host fallback (FIX 5, implemented)

`resolve_containment_target` no longer falls back to host when account identity signals are present but corroboration is insufficient. Gate escalates `ambiguous_target_identity` via the `target is None` path. The in-gate `evaluate_account_containment_eligibility` call remains defensive for resolved account targets (already corroborated at resolution time).

## REVIEW-007 — NeverContainSnapshotRecord placement (FIX 4a, **decision needed**)

`spec.md:236` requires a `NeverContainSnapshotRecord` whenever `auto_contain` is proposed and the live check runs. Current gate emits the directive only; `engine/edict.py` writes the snapshot at edict append with the **full** live list (audit semantics per `spec.md:240` / `contracts.md` §9 relationship paragraph).

**Options for your decision:**

1. **Inside gate transaction** — append snapshot record in the same `critical_transaction` as directive/idempotency/rate-limit writes. Risk: couples gate to ledger append before engine wiring exists.
2. **Deferred to engine edict-append wiring** — gate returns `live_never_contain_entries`; engine writes snapshot + edict together (current edict path). Risk: window between gate commit and edict append unless both move atomically in wiring task.

**Recommendation:** Option 2 — keep audit snapshot paired with `DecisionEdict` append; do not duplicate snapshot writes inside gate alone.

## REVIEW-008 — Expired-directive supersession revocation (FIX 4b, **decision needed**)

Expired-directive re-issue sets `supersedes_directive_id` but writes no `DirectiveRevocationRecord(reason=supersession)`. `spec.md:263` lists supersession as a revocation trigger with feed row; `contracts.md` §4.2 says expired keys permit a new directive with supersession reference but does not explicitly exempt the revocation record.

**Question:** Does an **expired** (not outstanding) directive require a supersession revocation record + feed row, or is the `supersedes_directive_id` field on the new directive sufficient because the prior directive is already past `expires_at`?

**Do not implement until you confirm.**

## REVIEW-009 — ContainmentDirective §9 hash (FIX 1, implemented)

`live_never_contain_hash` on `ContainmentDirective` now hashes `embedded_never_contain_entries` (target-relevant subset). `DecisionEdict.live_never_contain_hash` / `NeverContainSnapshotRecord` unchanged (full live list).

## Known gaps

- Engine orchestrator still uses `skeleton_policy_result`; PolicyGate not wired into intake/edict append.
- REVIEW-007 / REVIEW-008 pending your decisions before further code.
- Orphan outstanding directives without ledger edicts are skipped by step 6; duplicate emission risk documented in `test_reconcile_skips_idempotency_when_ledger_edict_missing`.
- Rate-limit scope uses `per_host` key for all target types in v1.
