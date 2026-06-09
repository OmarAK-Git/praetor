# Workflow Plan

## Goal

Implement TASK-018: Transactional rate limits and containment circuit breaker with race-safe sliding windows, multi-scope checks, and breaker health alerts.

## Scope

### In scope

- `praetor.policy.rate_limit` — sliding-window per-host/subnet/asset-group limits from org config scopes
- `praetor.policy.circuit_breaker` — containment breaker failures/successes, trip alert, counter freeze while open
- Wire modules into `praetor.policy.gate` and refactor `praetor.policy.state` persistence helpers
- Tests: `tests/policy/test_rate_limits.py`, `tests/policy/test_containment_circuit_breaker.py`

### Out of scope

- Engine orchestrator wiring
- Provider-health breaker (Task 19)
- Docs changes (`docs/` hard limit)
- Org-config schema changes (scopes-only `RateLimitPolicy`; limit=1 per scope per window per Task 17 ceiling)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Per-host, per-subnet, and per-asset-group limits block excess containment |
| REQ-002 | Unregistered target contributes to `per_host` only |
| REQ-003 | Concurrent attempts serialized (no race bypass) |
| REQ-004 | Sliding-window rate-limit failures trip containment breaker |
| REQ-005 | Breaker trip emits durable health alert |
| REQ-006 | Rate-limit counters persist unchanged through tripped period |
| REQ-007 | `success_reset_threshold` successes reset breaker failure state |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–003 | `tests/policy/test_rate_limits.py` pass |
| AC-002 | REQ-004–007 | `tests/policy/test_containment_circuit_breaker.py` pass |
| AC-003 | Integration | Existing `tests/policy/test_policy_gate.py` pass |
| AC-004 | Regression | Full `pytest`, `mypy src`, `ruff check src tests` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Rate limit module + scope resolution | `policy/rate_limit.py` | pending |
| T-002 | Containment circuit breaker module | `policy/circuit_breaker.py` | pending |
| T-003 | Gate + state integration | `policy/gate.py`, `policy/state.py` | pending |
| T-004 | Tests + verification | `tests/policy/test_*.py`, `.workflow/TASK-018/*` | pending |

## Risks

- Org config defines scopes but not numeric per-scope ceilings; v1 uses limit=1 per scope per `containment_circuit_breaker_policy.window_seconds` (Task 17 `_V1_DEFAULT_SCOPE_LIMIT` behavior with sliding windows).
- Subnet/asset-group membership uses asset registry only; unregistered hosts skip those scopes per plan criterion.
