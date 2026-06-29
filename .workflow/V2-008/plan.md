# Workflow Plan — V2-008 Compound Fault Flag Preservation

## Goal

Pin DEC-053 audit-flag fidelity: when stamp `FAILED` coincides with `DeferredDirectivePersistConflict`, the rebuilt escalate edict preserves both the conflict fault flag and `ticket_stamp_failed`; fail-closed disposition and directive suppression remain unchanged.

## Scope

### In scope

- Contract-level unit test mirroring orchestrator compound-fault rebuild (`test_stamp_sequencing.py`).
- Confirm existing orchestrator conflict path re-applies `apply_terminal_stamp_to_disposition` (already on HEAD).
- Confirm integration test `test_failed_stamp_and_deferred_persist_conflict_preserves_both_fault_flags` (already on HEAD).
- Close DEC-053 known-fidelity-gap note in `memory-bank/decisions.md`.
- Flight Recorder + Memory Bank updates.

### Out of scope

- `docs/` changes (hard limit).
- Recovery downgrade semantics (PE-0007 / PE-0025 unchanged).
- V2-006 escalate-blocking policy semantics.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Stamp `FAILED` + deferred persist conflict preserves `ticket_stamp_failed` and conflict fault flag. |
| REQ-002 | Compound path remains fail-closed: `escalate`, no outstanding directive. |
| REQ-003 | Normal stamp-failed and recovery paths unchanged (PE-0021 / PE-0025). |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Contract + intake tests assert both fault flags on compound path. |
| AC-002 | REQ-002 | Intake compound test asserts zero outstanding directives and `escalate` final disposition. |
| AC-003 | REQ-003 | Existing `test_stamp_sequencing.py` and recovery stamp-failed tests pass unchanged. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Contract unit test for compound fault flag append | `tests/tickets/test_stamp_sequencing.py` | complete |
| T-002 | Verify orchestrator conflict rebuild (no code change) | `src/praetor/engine/orchestrator.py` | complete |
| T-003 | Verify intake integration test (no change) | `tests/engine/test_intake_stamp_actuation.py` | complete |
| T-004 | Close DEC-053 gap note + Memory Bank | `memory-bank/*` | pending |
| T-005 | Verification + flight recorder | `.workflow/V2-008/*` | pending |

## Decision alignment

- **DEC-053:** compound-fault rebuild must re-apply `apply_terminal_stamp_to_disposition` after `escalate_disposition`.
- **PE-0021 / PE-0025:** stamp contract preserves caller disposition; recovery downgrade unchanged.
