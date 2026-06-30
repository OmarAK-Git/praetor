# Workflow Plan — V2-014 Correlator Host Isolation

## Goal

Drop in-window cross-host telemetry during correlation so the bundle is anchor-host scoped; PolicyGate citation anchoring is no longer the sole defense against unrelated hosts (AG-0080 / REVIEW-004).

## Scope

### In scope

- Anchor-host resolution and cross-host event filtering in `correlate_telemetry`
- Optional explicit `anchor_host_id` parameter
- Remove strict xfail on `test_correlator_should_drop_cross_host_in_window_noise`
- Update correlation expected YAML for noisy scenarios (1004 excluded; same-host incidental noise 1003 retained)
- Phase 3 regression assertions aligned with host-scoped bundles
- Unit tests for host isolation primitive

### Out of scope

- Orchestrator gate-target ownership (V2-015)
- `docs/` edits
- PolicyGate citation-anchored targeting logic (unchanged)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | `correlate_telemetry` filters in-window events to the anchor host |
| REQ-002 | Cross-host record 1004 excluded; same-host incidental noise 1003 retained |
| REQ-003 | Out-of-window exclusion (9999) unchanged |
| REQ-004 | Citation-anchored host targeting tests continue to pass |
| REQ-005 | Correlation accuracy + phase 3 gates green |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `test_correlator_should_drop_cross_host_in_window_noise` passes (xfail removed) |
| AC-002 | REQ-002 | Noisy expected YAML + gate tests: 1004 not collected; 1003 bounded |
| AC-003 | REQ-003 | Window boundary scenario still excludes 9999 |
| AC-004 | REQ-004 | `test_citation_anchored_host_targeting.py` green |
| AC-005 | REQ-005 | Full pytest, correlation gate, phase3 gate |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Host isolation primitive | `src/praetor/correlation/host_isolation.py` | pending |
| T-002 | Wire into `correlate_telemetry` | `src/praetor/correlation/__init__.py` | pending |
| T-003 | Unit tests | `tests/correlation/test_host_isolation.py` | pending |
| T-004 | Update expected YAML + regression tests | `evals/correlation_expected/`, `tests/evals/` | pending |
| T-005 | Remove xfail | `tests/evals/test_phase3_regression_gate.py` | pending |

## Risks

- Anchor derivation without security events relies on Sysmon plurality (documented in review if ambiguous).
- `otrf_unrelated_in_window_noise` scenario semantics shift from bounded overcollection to exclusion.
