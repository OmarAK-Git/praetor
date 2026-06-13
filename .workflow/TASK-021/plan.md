# Workflow Plan: TASK-021 — Reference Consumer Verifier

## Goal

Implement the reference consumer pre-actuation verifier outside `src/praetor/` per `docs/plan.md` Task 21 and `docs/contracts.md` §10.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `consumer_sdk/reference_verifier.py` — protocol checks 1–5 from §10
- `tests/consumer_sdk/test_reference_verifier.py` — plan test-first criteria
- `.workflow/TASK-021/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit; plan lists `docs/contracts.md` — gap recorded)
- Local consumer policy check (§10 item 6)
- Engine orchestrator / PolicyGate wiring
- Packaging consumer_sdk as separate distribution

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Expired directive → non-actionable with structured `failed_check` |
| REQ-002 | Revoked directive → non-actionable |
| REQ-003 | Embedded never-contain hash mismatch → escalate-human |
| REQ-004 | Feed cursor below `minimum_feed_sequence_at_issue` → escalate-human |
| REQ-005 | Feed stale beyond propagation delay + skew → escalate-human |
| REQ-006 | Feed sequence gap → escalate-human |
| REQ-007 | Clock-sync uncertainty beyond configured skew → escalate-human |
| REQ-008 | Overlapping target/scope lineage conflict → escalate-human |
| REQ-009 | Valid directive + fresh feed + no revocation → actionable |
| REQ-010 | Result includes `directive_id`, `target`, `failed_check`, `last_seen_sequence`, `consumer_clock_at_check`, `expires_at` |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–010 | `tests/consumer_sdk/test_reference_verifier.py` pass |
| AC-002 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests consumer_sdk` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Result types + §10 ordered checks | `consumer_sdk/reference_verifier.py` | complete |
| T-002 | Test-first scenarios from plan | `tests/consumer_sdk/test_reference_verifier.py` | complete |
| T-003 | Verification + Memory Bank | workflow + memory-bank | complete |

## Risks

- Lineage conflict algorithm is underspecified in docs; minimal overlap detection for same live target+scope without valid supersession feed row.
- SDK imports `praetor.contracts` and `praetor.hashing` only (not production containment modules).
