# Workflow Plan: TASK-030

## Goal

Implement a correlation accuracy gate that measures correlation quality on committed OTRF-style telemetry before judgment is trusted on real shapes.

## Scope

### In scope

- Add `evals/correlation_gate.py` — manifest checksum verification, scenario runner, pass/fail result.
- Add `evals/correlation_expected/*.yaml` — human-authored expected outputs for known scenarios.
- Add `tests/evals/test_correlation_gate.py` — test-first gate assertions.
- Verify fixture manifest checksums before any gate run.
- Assert known scenario collects required events and process relationships.
- Assert in-window noise overcollection stays below configured threshold.
- Assert missing required relationships fail the gate.

### Out of scope

- Phase 3 harness on correlated telemetry (TASK-031).
- Bulk OTRF/Mordor dataset download (deferred; committed fixtures stand in).
- Modify `docs/`.
- Wire gate into CI harness CLI (TASK-031).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Known OTRF-style scenario collects expected events per committed expected YAML. |
| REQ-002 | In-window noise overcollection stays below configured threshold. |
| REQ-003 | Missing required process relationships fail the gate. |
| REQ-004 | Fixture manifest checksums verified before gate runs. |
| REQ-005 | Gate module is runnable and testable from `evals/correlation_gate.py`. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Pass scenario YAML asserts required record IDs and relationships present after `correlate_telemetry`. |
| AC-002 | REQ-002 | Noisy scenario with `max_noise_overcollection: 1` passes; threshold `0` fails. |
| AC-003 | REQ-003 | Gate fails when expected parent/child relationship absent from correlated bundle. |
| AC-004 | REQ-004 | Tampered manifest checksum or pre-gate verification failure blocks gate with explicit error. |
| AC-005 | REQ-005 | `tests/evals/test_correlation_gate.py` exercises gate; `python -m evals.correlation_gate` exits 0 on pass. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Use committed `tests/fixtures/sysmon` + `tests/fixtures/security` as OTRF-style scenarios. | Same precedent as TASK-028/029; no external download in v1. |
| DEC-002 | Record IDs in expected YAML match fixture `record_id` fields parsed from `raw_source`. | Stable human-authored expectations independent of hash-derived `evidence_id`. |
| DEC-003 | Noise overcollection counts facts whose `record_id` appears in `noise_fixtures` inputs. | Separates required signal from optional in-window noise. |
| DEC-004 | Full manifest checksum verification runs before every gate scenario. | Plan requires manifest integrity before gate execution. |
| DEC-005 | Default pytest runs gate tests (no `integration` marker). | Committed fixtures only; matches TASK-029 reopen precedent. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing correlation gate tests (test-first). | `tests/evals/test_correlation_gate.py`, `evals/correlation_expected/*.yaml` | complete |
| TASK-002 | Implement `evals/correlation_gate.py`. | `evals/correlation_gate.py` | complete |
| TASK-003 | Run verification; update workflow + Memory Bank. | `.workflow/TASK-030/*`, `memory-bank/*` | complete |

## Risks

- Plan wording "marked integration" and "OTRF scenario" imply external datasets; v1 uses committed fixtures with gap recorded in `review.md`.
- Task 31 `noisy_correlated_real_telemetry` expected file is separate scope.
