# Workflow Plan: TASK-022 — Latency SLA and Queue Aging

## Goal

Implement provider latency SLA tracking and queue-aging detection per `docs/plan.md` Task 22, producing distinct Outcome Matrix fault flags with `system_fault_escalation=true`.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `src/praetor/engine/timeouts.py` — provider call timing and SLA exceeded detection
- `src/praetor/engine/queue_policy.py` — attempt queue-age evaluation from org config
- `tests/engine/test_latency_and_queue_aging.py` — plan test-first criteria
- Minimal orchestrator wiring for intake-time checks
- Minimal recovery hook for aged non-terminal attempts (criterion: no indefinite pending without visible fault)
- `.workflow/TASK-022/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit)
- Org-config field for provider latency SLA (contract pins only `max_queue_age_seconds`; v1 provisional constant)
- Full PolicyGate orchestrator replacement (flags already exist in `policy/gate.py`)
- Metrics (Task 24)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Provider latency beyond SLA → `escalate(latency_sla_exceeded)` |
| REQ-002 | Queue age beyond configured max → `escalate(queue_aging_exceeded)` |
| REQ-003 | Both faults carry `system_fault_escalation=true` |
| REQ-004 | No alert remains pending indefinitely without visible escalated fault |
| REQ-005 | Distinct Outcome Matrix fault flags (not conflated with `provider_timeout`) |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–005 | `tests/engine/test_latency_and_queue_aging.py` pass |
| AC-002 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Provider latency tracking | `engine/timeouts.py` | pending |
| T-002 | Queue aging policy | `engine/queue_policy.py` | pending |
| T-003 | Intake + recovery wiring | `engine/orchestrator.py`, `engine/recovery.py` | pending |
| T-004 | Tests + verification | `tests/engine/test_latency_and_queue_aging.py` | pending |
| T-005 | Memory Bank + flight recorder | `.workflow/TASK-022/*`, `memory-bank/*` | pending |

## Risks

- `LatencyAndQueueAgingPolicy` contract lacks `max_provider_judgment_latency_seconds`; v1 uses module constant (DEC-039) until doc/contract pin.
- Recovery change for aged attempts is minimal but outside plan file list; required by REQ-004.
