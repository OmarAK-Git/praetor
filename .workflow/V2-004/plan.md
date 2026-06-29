# Workflow Plan — V2-004 Provider Unavailable Outcome Matrix Row

## Goal

Ratify `provider_unavailable` as a documented Outcome Matrix fault flag for `ProviderUnavailableError`, wire enum/metrics/harness completeness guards, and enable intake to emit the canonical flag (not a runtime-only string). Provider-health breaker tripping remains independent of edict mapping.

## Scope

### In scope

- **DEC-061** in `docs/decisions.md` — `provider_unavailable` semantics vs other provider faults and breaker.
- `docs/contracts.md` §13 Outcome Matrix row.
- `docs/proposals/delivery_backlog.md` — close P1 ProviderUnavailable intake row.
- `OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE`, `OUTCOME_MATRIX_SFE`, `LLM_FAILURE_FAULT_FLAGS`.
- `FakeProviderMode.UNAVAILABLE`, harness scenario `provider_unavailable.yaml`.
- Minimal `process_alert_intake` catch mapping to `_finish_provider_fault`.
- Targeted tests in `tests/evals/` and `tests/judgment/`.

### Out of scope

- Full metrics production wiring audit (V2-020).
- Static fault-flag guard on `DecisionEdict` (V2-016).
- `docs/spec.md` mirror — frozen until spec unfreeze.
- Provider retry policy changes for unavailable errors.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | §13 Outcome Matrix row: `ProviderUnavailableError` → `escalate` / `provider_unavailable` / `system_fault_escalation=true`. |
| REQ-002 | `OutcomeMatrixFaultFlag` enum + `evals/outcome_matrix.py` SFE polarity aligned with §13. |
| REQ-003 | `LLM_FAILURE_FAULT_FLAGS` includes `provider_unavailable` for metrics validation. |
| REQ-004 | Harness completeness guard covers `provider_unavailable`; scenario SFE matches canonical map. |
| REQ-005 | Intake catches `ProviderUnavailableError` using enum value (no ad-hoc fault string). |
| REQ-006 | Provider-health breaker still trips on `ProviderUnavailableError` independently of edict flag choice. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | DEC-061 + contracts §13 row after `provider_refusal`. |
| AC-002 | REQ-002 | Enum member + `OUTCOME_MATRIX_SFE[PROVIDER_UNAVAILABLE] is True`. |
| AC-003 | REQ-003 | `PROVIDER_UNAVAILABLE in LLM_FAILURE_FAULT_FLAGS`. |
| AC-004 | REQ-004 | `test_outcome_matrix_completeness_guard` passes with `provider_unavailable.yaml`. |
| AC-005 | REQ-005 | `process_alert_intake` + FakeProvider unavailable mode emits documented edict. |
| AC-006 | REQ-006 | `test_provider_unavailable_trips_breaker` still passes unchanged. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | DEC-061 + contracts §13 | `docs/decisions.md`, `docs/contracts.md` | pending |
| T-002 | Enum + outcome matrix + LLM flags | `metrics/events.py`, `evals/outcome_matrix.py` | pending |
| T-003 | FakeProvider + orchestrator catch | `fake_provider.py`, `orchestrator.py` | pending |
| T-004 | Harness scenario + tests | `evals/scenarios/`, `tests/evals/`, `tests/judgment/` | pending |
| T-005 | Backlog + Memory Bank + verification | `delivery_backlog.md`, `memory-bank/*`, `.workflow/V2-004/*` | pending |

## Decision summary (owner ratification)

1. **New fault flag `provider_unavailable`** — not mapped to `provider_timeout` or `provider_refusal`. Covers integration not configured, transport/upstream unavailability, and immediate typed `ProviderUnavailableError` before a successful judgment (distinct from bounded-retry timeout exhaustion).
2. **Disposition:** `escalate` with `system_fault_escalation=true` (infrastructure fault class; extends PE-0009 family).
3. **Breaker independence:** `ProviderUnavailableError` continues to trip the provider-health breaker (`provider_failure_trips_breaker`); final edict uses `provider_unavailable`, not `provider_health_breaker_open`, unless the breaker blocks the call first (existing breaker-open path unchanged).
