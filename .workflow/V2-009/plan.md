# Workflow Plan — V2-009 Emergency Never-Contain Gate Alignment

## Goal

Align emergency never-contain with containment **authorization** (PolicyGate + intake), not only revocation/recovery reconciliation. Confirm unified ledger append on automated revocation paths and add engine-intake harness coverage.

## Scope

### In scope

- PolicyGate live never-contain authorization uses `emergency.py` authorization helper (documented layer).
- `engine_intake` harness applies `emergency_never_contain` setup (parity with `policy_gate` runner).
- New eval scenario: emergency blocks on full intake path.
- Integration test: pre-seeded emergency blocks containment before stamp.
- Document unified revocation ledger policy in `review.md` (all paths via `automated_revoke_directive_in_transaction`).

### Out of scope

- `docs/` changes (hard limit).
- Recovery pinning / orphan health surfacing (V2-010).
- Never-contain snapshot timing changes (DEC-060 settled in V2-003).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Active emergency entries block `auto_contain` at PolicyGate authorization layer. |
| REQ-002 | Activation, emergency, and recovery revocation paths share ledger append via `automated_revoke_directive_in_transaction`. |
| REQ-003 | Harness or integration scenario covers emergency conflict on the intake path. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Gate + policy tests: live emergency → escalate `never_contain_live_conflict`. |
| AC-002 | REQ-002 | Existing activation/emergency/recovery tests assert `directive_revocation` ledger rows; documented in review. |
| AC-003 | REQ-003 | `emergency_never_contain_intake.yaml` passes; `test_intake_emergency_never_contain_blocks_at_authorization` green. |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Authorization helper + gate wiring | `config/emergency.py`, `policy/gate.py` | pending |
| T-002 | Engine intake harness emergency setup | `evals/harness.py` | pending |
| T-003 | Intake scenario + integration test | `evals/scenarios/`, `tests/engine/` | pending |
| T-004 | Verification + flight recorder | `.workflow/V2-009/*`, `memory-bank/*` | pending |

## Decision alignment

- **DEC-060 (V2-003):** Gate is pure evaluator; snapshot at edict-append only.
- **PE-0007:** Recovery cannot emit new auto-contain (unchanged).
- **AG-0044:** `live_never_contain_entries` captured at gate eval for engine snapshot.
