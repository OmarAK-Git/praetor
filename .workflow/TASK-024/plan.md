# Workflow Plan: TASK-024 — Metrics

## Goal

Implement the Praetor metrics collector (`metrics/events.py`, `metrics/collector.py`) covering all Task 24 test-first criteria from `docs/plan.md`, including feed export lag health (per-record lag, p99, warning threshold, unhealthy transitions).

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `src/praetor/metrics/events.py` — typed metric event kinds and snapshot models
- `src/praetor/metrics/collector.py` — in-process collector with independent counter domains
- `tests/metrics/test_metrics.py` — all plan test-first criteria
- `tests/contracts/test_scope_guard.py` — allow `metrics` package
- `.workflow/TASK-024/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit)
- Wiring collector into orchestrator / PolicyGate / exporter (follow-on integration)
- Prometheus/OTLP export format
- Future tasks (25+)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Disposition distribution counters increment per final disposition |
| REQ-002 | PolicyGate override counter increments when proposed ≠ final |
| REQ-003 | LLM failure counters increment per fault flag |
| REQ-004 | Containment directive emitted counter increments |
| REQ-005 | Queue-aging fallback counter increments |
| REQ-006 | Provider-health and containment breaker state metrics are independent |
| REQ-007 | Probe outcome metrics independent from production call metrics |
| REQ-008 | Probe rate-limit metric tracks configured `probe_rate_limit_per_minute` |
| REQ-009 | Stamp status counter increments per terminal/non-terminal status |
| REQ-010 | Health-alert delivery status counter increments per channel outcome |
| REQ-011 | Feed export lag recorded per successful export from `ledger_commit_at` |
| REQ-012 | p99 feed export lag and warning-threshold metrics exist |
| REQ-013 | `revocation_feed_unhealthy` transition counter increments |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–013 | `tests/metrics/test_metrics.py` pass |
| AC-002 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests consumer_sdk` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Workflow artifacts | `.workflow/TASK-024/*` | completed |
| T-002 | Tests + metrics module | `metrics/*`, `tests/metrics/*`, scope guard | in_progress |
| T-003 | Verification + Memory Bank | `.workflow/TASK-024/*`, `memory-bank/*` | pending |

## Risks

- p99 on small sample sets: use standard nearest-rank percentile for v1.
- Probe/production independence already lives in `provider_health_metrics` table; collector mirrors in-memory for tests and future wiring.

## Verification plan

- `python -m pytest -q tests/metrics/test_metrics.py`
- `python -m pytest -q`
- `python -m mypy src`
- `python -m ruff check src tests consumer_sdk`
