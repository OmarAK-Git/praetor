# Workflow Plan: TASK-035

## Goal

Deliver a production throughput benchmark for the full serialized SQLite path and operator-facing documentation (`operator_runbook.md`, `architecture.md`) so a new operator can understand contracts, responsibility boundaries, feed behavior, failure modes, phase gates, and residual risks without reading source.

## Scope

### In scope

- `benchmarks/serialized_path.py` — full serialized path vs `provisional_alert_rate_targets`.
- `docs/operator_runbook.md` — deployment constraints, failure recovery, feed/ledger guidance, throughput ceiling.
- `docs/architecture.md` — system overview referencing generated schemas.
- `docs/contracts.md` — throughput benchmark cross-reference (minimal addition).
- `docs/eval_gates.md` — phase gate commands and pass criteria.
- `tests/docs/test_docs.py` — required-section checks.
- `tests/benchmarks/test_serialized_path.py` — benchmark tests.
- `tests/contracts/test_scope_guard.py` — allow Phase 5 docs.
- Splunk env-gated integration test + README/splunk README HEC reconciliation.

### Out of scope

- Modify `docs/plan.md`, `docs/spec.md`, `docs/prd.md`.
- Horizontal scaling, feed rotation machinery, provider tokenizer API.
- Live Splunk demo execution in CI (env-gated only).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Production benchmark uses Sprint 1 `provisional_alert_rate_targets` from active org config. |
| REQ-002 | Benchmark measures full serialized SQLite path: prev-hash lookup, hash, insert, idempotency, rate-limit update, live never-contain check, feed-health check, feed outbox where applicable. |
| REQ-003 | Throughput ceiling documented in `docs/operator_runbook.md`. |
| REQ-004 | Docs reference generated `schemas/`; disposition vocabulary uses `standard_review`, not `pass`. |
| REQ-005 | Runbook covers all topics listed in `docs/plan.md` Task 35 test-first criteria. |
| REQ-006 | `tests/docs/test_docs.py` validates required runbook/architecture/eval-gate content. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Benchmark loads targets from active snapshot; tests assert example org 30/60. |
| AC-002 | REQ-002 | Each benchmark iteration runs policy-gate emit + ledger append + revocation feed outbox in one critical transaction. |
| AC-003 | REQ-003 | Runbook includes measured-ceiling section with benchmark command and interpretation. |
| AC-004 | REQ-004 | Doc tests grep for `standard_review` and schema paths; no standalone disposition `pass` enum. |
| AC-005 | REQ-005 | Doc tests assert required runbook section headings/topics. |
| AC-006 | REQ-006 | `pytest tests/docs/` passes. |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| TASK-001 | Workflow + failing tests | `.workflow/TASK-035/*`, `tests/docs/*`, `tests/benchmarks/*` | pending |
| TASK-002 | Benchmark implementation | `benchmarks/serialized_path.py` | pending |
| TASK-003 | Operator docs | `docs/operator_runbook.md`, `docs/architecture.md`, `docs/contracts.md`, `docs/eval_gates.md` | pending |
| TASK-004 | Scope guard, Splunk, README | `tests/contracts/test_scope_guard.py`, splunk tests, README | pending |
| TASK-005 | Verification + Memory Bank | workflow close-out | pending |

## Risks

- Benchmark rate on developer hardware is not production capacity — runbook must state measurement context.
- Runbook breadth is large — use section tests with keyword anchors, not brittle full-text equality.
