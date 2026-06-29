# Workflow Plan — V2-010 Recovery Policy Pinning

## Goal

Pin startup recovery semantics per DEC-060: retain and test `auto_contain` downgrade on recovery paths; surface orphan outstanding directives (no ledger edict) as operator-visible health alerts; preserve startup step ordering (engine recovery before feed recovery).

## Scope

### In scope

- Explicit tests for recovery `auto_contain` → `escalate` downgrade (success and failed stamp paths).
- `fetch_orphan_outstanding_directives` + `orphan_outstanding_directive` health alert emission at engine startup recovery.
- `StartupRecoveryResult` extended with orphan alert IDs.
- Step-order regression test: `open_state_store` runs engine recovery before feed export.
- Flight recorder + memory bank updates.

### Out of scope

- `docs/` changes (hard limit).
- Orphan directive purge (DEC-060 forbids automatic purge without recovery context).
- Expired-unrevoked row archival (optional per DEC-060; deferred).
- PolicyGate re-evaluation path (retain existing downgrade; no replacement).
- V2-009 emergency never-contain alignment.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Recovery paths downgrade `auto_contain` candidates to `escalate`; never emit containment on recovery. |
| REQ-002 | Orphan outstanding directives (no ledger edict) emit `orphan_outstanding_directive` health alert at startup. |
| REQ-003 | Step 6 skips orphan idempotency re-registration (existing); does not paper over orphans. |
| REQ-004 | Startup ordering: singleton/SQLite guard → state open → engine recovery (4–7) → feed recovery (8). |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Unit test on `_recovery_disposition_for_stamp` + integration tests for failed/succeeded stamp recovery. |
| AC-002 | REQ-002 | Test: orphan directive → health alert in outbox after `run_engine_startup_recovery` / `open_state_store`. |
| AC-003 | REQ-003 | Existing `test_reconcile_skips_idempotency_when_ledger_edict_missing` remains green; no idempotency registered. |
| AC-004 | REQ-004 | Existing feed-after-engine test remains green; no reorder in `open_state_store`. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Orphan detection + alert helpers | `policy/state.py`, `containment/revocation.py` | pending |
| T-002 | Wire orphan surfacing in engine recovery | `engine/recovery.py` | pending |
| T-003 | Recovery downgrade + orphan tests (TDD) | `tests/engine/`, `tests/policy/` | pending |
| T-004 | Verification + flight recorder | `.workflow/V2-010/*`, `memory-bank/*` | pending |

## Decision alignment

- **DEC-060 (V2-003):** Orphans skipped at step 6; health surfacing in V2-010; no automatic purge.
- **PE-0007 / PE-0023:** Recovery downgrade is caller responsibility in `recovery.py`; stamp contract preserves caller disposition.
