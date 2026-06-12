# Workflow Plan: TASK-020 — Directive Lifecycle and Revocation

## Goal

Implement the `praetor.containment` package consolidating directive lifecycle (proposed→emitted) and differentiated revocation triggers with ledger + feed projection per `docs/plan.md` Task 20.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `src/praetor/containment/{__init__,lifecycle,revocation}.py`
- Refactor callers: `policy/gate.py`, `policy/directive_builder.py`, `config/directives.py`, `config/activation.py`, `config/emergency.py`, `engine/recovery.py`
- Tests: `tests/containment/test_directive_lifecycle.py`, `tests/containment/test_revocation.py`
- Scope guard: allow `containment` package

### Out of scope

- `docs/` edits (command hard limit)
- Reference consumer verifier (Task 21)
- Engine orchestrator PolicyGate wiring
- Supersession via PolicyGate (v1 suppresses live re-issue; API defined for Task 21)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | `ContainmentDirective.status` transitions `proposed` → `emitted` on commit |
| REQ-002 | Directive lifetime ≤ 300 seconds (contract validator) |
| REQ-003 | Account `target_id` is SID form |
| REQ-004 | Embedded never-contain entries + `live_never_contain_hash` |
| REQ-005 | `minimum_feed_sequence_at_issue` = last verified-exported sequence |
| REQ-006 | Consumer can verify embedded entries hash |
| REQ-007 | Revocation writes ledger record + feed outbox row |
| REQ-008 | Post-emission never-contain conflict: health alert; key not cleared |
| REQ-009 | Manual revocation: record + feed + key clear in one transaction |
| REQ-010 | Supersession: `superseded_by_directive_id` set; key not cleared |
| REQ-011 | Post-activation reconciliation: revocation + feed + health alert |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–006 | `tests/containment/test_directive_lifecycle.py` pass |
| AC-002 | REQ-007–011 | `tests/containment/test_revocation.py` pass |
| AC-003 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Lifecycle module (build, emit, persist, hash verify) | `containment/lifecycle.py` | complete |
| T-002 | Revocation module (differentiated triggers) | `containment/revocation.py` | complete |
| T-003 | Refactor callers + scope guard | policy, config, engine | complete |
| T-004 | Tests + verification | `tests/containment/*` | complete |

## Risks

- Thin re-exports in `config/directives.py` and `policy/directive_builder.py` preserve existing import paths.
- Manual revocation ledger append remains caller responsibility (StateStore API unchanged from Task 6).
