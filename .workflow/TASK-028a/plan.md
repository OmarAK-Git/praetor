# Workflow Plan: TASK-028a

## Goal

Wire `evaluate_policy_gate` and `MetricsCollector` into `process_alert_intake` using correlation-aware `EvidenceBundle` resolution (Task 28), convert strict-xfail tripwires to passing tests, and route `confirmed_malicious_sequence` / `never_contain_target` through `engine_intake` eval runner.

## Scope

### In scope

- Correlation-aware bundle resolution in orchestrator (telemetry events, explicit override, skeleton default)
- PolicyGate evaluation replacing skeleton `auto_contain → escalate` downgrade
- Metrics recording at intake call sites
- Tripwire test conversion (remove xfail markers)
- Eval scenario runner switch for two gate scenarios
- Harness `engine_intake` bundle/provider alignment
- Focused orchestrator metrics integration tests

### Out of scope

- Full DEC-028 gate/orchestrator transaction merge (gate retains internal emit tx; note gap)
- Task 29–31 correlation gates
- `docs/` changes

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | `process_alert_intake` calls `evaluate_policy_gate` with correlated bundle |
| REQ-002 | `auto_contain` passes when all deterministic gates pass |
| REQ-003 | Never-contain snapshot blocks via PolicyGate on intake path |
| REQ-004 | `MetricsCollector` records disposition/override/breaker at intake |
| REQ-005 | Tripwire tests pass without xfail |
| REQ-006 | `engine_intake` evals drive gated auto_contain and never-contain block |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `evaluate_policy_gate` in orchestrator source; gate invoked on happy path |
| AC-002 | REQ-002 | Tripwire + eval `confirmed_malicious_sequence` → `auto_contain` |
| AC-003 | REQ-003 | Tripwire + eval `never_contain_target` → escalate + `never_contain_snapshot` |
| AC-004 | REQ-004 | Metrics tests assert collector updates from intake |
| AC-005 | REQ-005 | `test_policygate_integration_tripwire.py` green without xfail |
| AC-006 | REQ-006 | Harness scenarios use `runner: engine_intake` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T1 | Bundle hash helper + orchestrator wiring | `engine/ids.py`, `engine/orchestrator.py` | pending |
| T2 | Metrics hooks + integration tests | `engine/orchestrator.py`, `tests/metrics/*` | pending |
| T3 | Tripwire + eval scenario updates | `tests/engine/*`, `evals/scenarios/*`, `evals/harness.py` | pending |
| T4 | Verification + Memory Bank | `.workflow/TASK-028a/*`, `memory-bank/*` | pending |
