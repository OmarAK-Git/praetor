# Workflow Plan: TASK-023 — Ticket Stamp Contract Integration

## Goal

Integrate the ticket stamp Outcome Matrix contract into intake and recovery via `tickets/contract.py`, ensuring stamp failure preserves candidate disposition (never promotes `standard_review` to `escalate`) and no ledger edict is appended while a stamp is in-flight.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `src/praetor/tickets/contract.py` — stamp disposition sequencing helpers
- `tests/tickets/test_stamp_sequencing.py` — plan test-first criteria
- Minimal orchestrator wiring: apply contract after terminal stamp; defer edict on in-flight stamp
- Minimal recovery refactor: delegate disposition mapping to contract
- `.workflow/TASK-023/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit)
- Full PolicyGate orchestrator replacement (Task 17 follow-on)
- Metrics (Task 24)
- Changing UNKNOWN vs FAILED ambiguity mapping in `stamp.py` (Task 7 contract)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Stamp success preserves candidate disposition |
| REQ-002 | Stamp failure preserves `standard_review` and adds `ticket_stamp_failed` |
| REQ-003 | Stamp failure preserves `auto_contain` or `escalate` candidate and adds flag |
| REQ-004 | No ledger edict while stamp attempt is in-flight |
| REQ-005 | Unreachable/definitive ticket failure treated as stamp failure disposition |
| REQ-006 | `unknown` recovery resends same `stamp_id` |
| REQ-007 | One-disposition invariant holds on all stamp terminal paths |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–007 | `tests/tickets/test_stamp_sequencing.py` pass |
| AC-002 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Stamp contract module | `tickets/contract.py` | pending |
| T-002 | Sequencing tests | `tests/tickets/test_stamp_sequencing.py` | pending |
| T-003 | Intake + recovery wiring | `engine/orchestrator.py`, `engine/recovery.py` | pending |
| T-004 | Verification + flight recorder | `.workflow/TASK-023/*`, `memory-bank/*` | pending |

## Risks

- Orchestrator/recovery wiring outside plan file list; required for integration (same pattern as TASK-022).
- In-flight stamp intake returns incomplete `IntakeResult` (no edict); recovery completes later per spec.
