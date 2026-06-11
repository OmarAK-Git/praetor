# Workflow Plan

## Goal

Implement Task 19: provider-health circuit breaker with half-open synthetic probes, independent from the containment breaker domain.

## Scope

### In scope

- Add `src/praetor/judgment/provider_health_breaker.py` with failure tripping, health alert emission, half-open entry (SOC-lead + timer), rate-limited canary probes, and separate probe/production metric counters.
- Define synthetic canary payload constant on the provider Protocol module.
- Map `ProviderUnavailableError` (and other typed provider failures) as breaker-tripping production failures.
- Add `tests/judgment/test_provider_health_breaker.py` covering all Task 19 test-first criteria.
- Extend `circuit_breaker_state` schema for half-open tracking (`half_open`, `opened_at`).

### Out of scope

- Do not modify `docs/`.
- Do not catch `ProviderUnavailableError` in engine intake (no Outcome Matrix row yet).
- Do not wire production failure recording into orchestrator (Task follow-on).
- Do not implement Task 24 metrics collector (expose counters for independence tests only).
- Do not add auth WriteSurface (validate `soc_lead` role on trigger parameter).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Provider production failures trip provider-health breaker at configured threshold. |
| REQ-002 | Breaker trip emits distinct `provider_health_breaker_open` health alert. |
| REQ-003 | Production path blocked while breaker open or half-open (PolicyGate escalates). |
| REQ-004 | SOC-lead trigger enters half-open probe mode when breaker is open. |
| REQ-005 | Configured timer (`window_seconds` since open) enters half-open probe mode. |
| REQ-006 | Probes use fixed synthetic canary payload; no production alert data. |
| REQ-007 | Probes rate-limited by `probe_rate_limit_per_minute`. |
| REQ-008 | Probe success/failure metrics independent from production call metrics. |
| REQ-009 | Probe failure in half-open reopens breaker and resets success countdown. |
| REQ-010 | `success_reset_threshold` consecutive probe successes close breaker. |
| REQ-011 | Provider-health and containment breaker states are independent. |
| REQ-012 | `ProviderUnavailableError` maps to breaker-tripping provider failure. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Tests record N failures and observe `is_open=1` at threshold. |
| AC-002 | REQ-002 | Trip enqueues `provider_health_breaker_open` alert in outbox. |
| AC-003 | REQ-003 | Gate test with open provider-health breaker returns escalate + fault flag. |
| AC-004 | REQ-004 | SOC-lead trigger sets `half_open=1` while `is_open=1`. |
| AC-005 | REQ-005 | Timer elapse after `opened_at` auto-enters half-open. |
| AC-006 | REQ-006 | Probe invokes `provider.probe(canary)` only; canary constant exported. |
| AC-007 | REQ-007 | Excess probes within minute rejected without provider call. |
| AC-008 | REQ-008 | Production failure counter increments without probe counter change. |
| AC-009 | REQ-009 | Failed probe clears success_count and `half_open=0`. |
| AC-010 | REQ-010 | N probe successes set `is_open=0`. |
| AC-011 | REQ-011 | Tripping one domain leaves other domain unchanged. |
| AC-012 | REQ-012 | `provider_failure_trips_breaker(ProviderUnavailableError(...))` is True. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Add failing Task 19 tests. | `tests/judgment/test_provider_health_breaker.py` | pending |
| TASK-002 | Add canary constant to provider module. | `src/praetor/judgment/provider.py`, `__init__.py` | pending |
| TASK-003 | Implement provider health breaker module. | `src/praetor/judgment/provider_health_breaker.py` | pending |
| TASK-004 | Run verification; update workflow + Memory Bank. | `.workflow/TASK-019/*`, `memory-bank/*` | pending |

## Risks

- Half-open timer reuses `window_seconds` (no separate org-config field); record in review if ambiguous.
- Schema migration via ALTER for existing `circuit_breaker_state` rows.

## Verification plan

- `python -m pytest -q tests/judgment/test_provider_health_breaker.py`
- `python -m pytest -q tests/judgment/ tests/policy/test_policy_gate.py`
- `python -m pytest -q`
- `python -m mypy src`
- `python -m ruff check src tests`
