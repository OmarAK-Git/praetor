# Workflow Plan — V2-003 Revocation and Snapshot Owner Decisions

## Goal

Ratify REVIEW-007 (NeverContainSnapshotRecord placement), REVIEW-008 (expired-directive re-issue vs supersession revocation), and startup reconciliation semantics for expired-unrevoked rows and orphan outstanding directives so V2-009, V2-010, and V2-018 implement against one authoritative target.

## Scope

### In scope

- **DEC-060** in `docs/decisions.md` — snapshot placement, expired re-issue carve-out, startup reconciliation policy.
- `docs/contracts.md` — §4.2 startup reconciliation pins; §7a snapshot append site.
- `docs/proposals/delivery_backlog.md` — close REVIEW-007, REVIEW-008, expired-row, and orphan-directive decision rows.
- Memory Bank task status and context updates.
- Flight Recorder artifacts.

### Out of scope

- Production code changes (`edict.py`, `lifecycle.py`, `policy/state.py`) — V2-009, V2-010, V2-018.
- Activation/emergency ledger-append unification — V2-009.
- Orphan purge/health-alert implementation — V2-010.
- Feed supersession consumer verifiability — V2-018.
- `docs/spec.md` amendments — frozen until spec unfreeze.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Ratify `NeverContainSnapshotRecord` write site (gate vs engine edict-append). |
| REQ-002 | Ratify expired-directive fresh re-issue vs `DirectiveRevocationRecord` supersession. |
| REQ-003 | Specify startup behavior for expired-unrevoked rows in `outstanding_containment_directives`. |
| REQ-004 | Specify startup behavior for orphan outstanding directives without ledger edicts. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | DEC-060 + §7a: snapshot appended only in engine post-stamp transaction, paired atomically with `DecisionEdict`; gate does not append ledger records. |
| AC-002 | REQ-002 | DEC-060 + §4.2: expired re-issue needs no revocation record/feed row; `supersedes_directive_id` unset; live supersession still requires revocation record. |
| AC-003 | REQ-003 | DEC-060 + §4.2: expired-unrevoked rows may remain in table; excluded from step-6 idempotency re-registration; no purge required for correctness. |
| AC-004 | REQ-004 | DEC-060 + §4.2: orphans skipped at step 6; surfaced as health/audit condition in V2-010; no idempotency re-registration. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Draft DEC-060 decision text | `docs/decisions.md` | pending |
| T-002 | Pin contracts §4.2 / §7a semantics | `docs/contracts.md` | pending |
| T-003 | Close delivery backlog decision rows | `docs/proposals/delivery_backlog.md` | pending |
| T-004 | Update Memory Bank | `memory-bank/*` | pending |
| T-005 | Verification + flight recorder close | `.workflow/V2-003/*` | pending |

## Decision summary (owner ratification)

1. **REVIEW-007 / snapshot placement:** Option 2 — `NeverContainSnapshotRecord` is written **only** in the engine's terminal post-stamp `critical_transaction`, atomically paired with `DecisionEdict` (refines DEC-028/DEC-053). PolicyGate returns `live_never_contain_entries`; gate never appends ledger snapshot records.
2. **REVIEW-008 / expired re-issue:** Retain `docs/contracts.md` §4.2 carve-out (PE-0015). Natural expiry permits fresh re-issue on the same idempotency key with **no** `DirectiveRevocationRecord` and **no** feed row; `supersedes_directive_id` stays **unset**. Supersession revocation applies only when replacing a **still-live** (unexpired, unrevoked) directive.
3. **Expired-unrevoked rows:** May remain in `outstanding_containment_directives` as audit residue. `fetch_outstanding_unrevoked_directives` already filters `expires_at > now`, so step 6 does not re-register idempotency for expired rows and fresh re-issue is not blocked. Optional archival purge is V2-010, not required for correctness.
4. **Orphan directives (no ledger edict):** Startup step 6 **skips** idempotency re-registration (AG-0045). Orphans must be **surfaced** as an operator-visible health/audit condition (V2-010), not silently purged or re-registered. Engine startup recovery remains authoritative for half-committed attempts.
