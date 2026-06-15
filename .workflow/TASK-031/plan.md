# Workflow Plan: TASK-031

## Goal

Implement the Phase 3 regression gate that combines correlation accuracy on noisy real telemetry, identity compliance evidence, and Phase 2 safety invariants on Task 28 correlated `EvidenceBundle` output.

## Scope

### In scope

- Add `evals/run_phase3_gate.py` — orchestrates required expected file, correlation gate, identity compliance, account gate prerequisite, and safety checks on noisy bundle.
- Add `evals/correlation_expected/noisy_correlated_real_telemetry.yaml` — human-authored expected output for noisy OTRF-style fixtures.
- Add `tests/evals/test_phase3_regression_gate.py` — test-first gate assertions.

### Out of scope

- Modify `docs/`.
- Bulk OTRF/Mordor download (committed fixtures stand in per TASK-030).
- New mandatory Phase 2 scenario YAML (placeholder remains for Phase 2 harness).
- Tasks 32+.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Gate consumes correlated `EvidenceBundle` from Task 28 `correlate_telemetry` output. |
| REQ-002 | `noisy_correlated_real_telemetry` runs against committed real OTRF-style fixtures. |
| REQ-003 | Phase 2 safety invariants hold when evaluated on the noisy correlated bundle. |
| REQ-004 | Gate fails if human-authored `noisy_correlated_real_telemetry.yaml` is absent. |
| REQ-005 | Account containment cannot be enabled unless identity compliance tests pass. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Safety checks correlate telemetry via `correlate_telemetry` before policy/intake assertions. |
| AC-002 | REQ-002 | Correlation gate passes `noisy_correlated_real_telemetry.yaml` with bounded noise. |
| AC-003 | REQ-003 | Noisy bundle preserves corroboration; host `auto_contain` and account gate-off paths match Phase 2 invariants. |
| AC-004 | REQ-004 | Missing expected file yields explicit gate failure. |
| AC-005 | REQ-005 | Gate runs identity compliance tests; preflight rejects `account_auto_contain_enabled=true`. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Reuse committed `tests/fixtures/sysmon` + `security` as OTRF-style noisy scenario. | Same precedent as TASK-028/029/030. |
| DEC-002 | Combine ambiguous + unrelated in-window noise fixtures. | Exercises richer noisy real telemetry within manifest bounds. |
| DEC-003 | Identity compliance verified by running `test_correlator_identity_compliance.py`. | Plan requires evidence tests pass, not self-attestation. |
| DEC-004 | Phase 3 gate CLI optionally skips full Phase 2 harness for unit tests; CLI runs harness by default. | Keeps pytest fast; CLI remains comprehensive. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing phase 3 gate tests. | `tests/evals/test_phase3_regression_gate.py`, expected YAML | pending |
| TASK-002 | Implement `evals/run_phase3_gate.py`. | `evals/run_phase3_gate.py` | pending |
| TASK-003 | Run verification; update workflow + Memory Bank. | `.workflow/TASK-031/*`, `memory-bank/*` | pending |

## Risks

- Full Phase 2 harness in CLI gate is slow; mitigated by `include_harness` flag for tests.
- External OTRF datasets deferred; gap recorded in review.
