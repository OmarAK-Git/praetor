# Workflow Plan — V2-007 ProviderUnavailable Intake Handling

## Goal

Complete documented, tested intake disposition for `ProviderUnavailableError`: Outcome Matrix edict, provider-health breaker production-failure recording on the intake path, and metrics that record only approved LLM/provider fault flags.

## Scope

### In scope

- Harden `process_alert_intake` provider-unavailable path (DEC-061 / V2-004 baseline).
- Record provider-health breaker production failures when intake exits via typed provider faults.
- Engine + metrics tests for edict, breaker metrics, and `llm_failure_by_fault_flag`.
- Flight Recorder + Memory Bank updates.

### Out of scope

- Full metrics production audit (V2-020).
- Static fault-flag guard on `DecisionEdict` (V2-016).
- `docs/` modifications.
- Provider retry policy for unavailable errors.
- V2-006 escalate blocking (parallel branch).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | `process_alert_intake` catches `ProviderUnavailableError` and maps to `provider_unavailable`. |
| REQ-002 | Final edict: `escalate`, `system_fault_escalation=true`, documented fault flag. |
| REQ-003 | Provider-health breaker records production failure on intake provider-fault exit. |
| REQ-004 | Metrics record `provider_unavailable` under approved `LLM_FAILURE_FAULT_FLAGS` only. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Engine intake test: unavailable FakeProvider → documented edict. |
| AC-002 | REQ-002 | `assert_outcome_matrix_edict` with SFE=true on intake path. |
| AC-003 | REQ-003 | `read_provider_health_metrics().production_failure_total` increments after intake unavailable. |
| AC-004 | REQ-004 | `MetricsCollector.snapshot().llm_failure_by_fault_flag["provider_unavailable"] == 1`; flag ∈ `LLM_FAILURE_FAULT_FLAGS`. |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Tests-first intake + metrics coverage | `tests/engine/`, `tests/metrics/` | pending |
| T-002 | Breaker failure hook on provider-fault persist | `orchestrator.py`, `edict.py` | pending |
| T-003 | Metrics breaker gauge on provider-fault path | `orchestrator.py` | pending |
| T-004 | Workflow + Memory Bank + verification | `.workflow/V2-007/*`, `memory-bank/*` | pending |

## Risks

- Breaker recording must run inside the same `critical_transaction` as edict persist (`require_critical_transaction` on breaker helper).
- Distinct edict flag `provider_unavailable` vs `provider_health_breaker_open` when breaker trips (DEC-061).
