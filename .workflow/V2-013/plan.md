# Workflow Plan — V2-013 Default-Deny / Configurable Posture Flip

## Goal

Remove remaining implicit-allow dependencies: eval harness, walkthrough, and example config express explicit permits; no-rule targets escalate via `default_action`, not omission.

## Scope

### In scope

- Replace harness `default_action=auto_contain` permissive override with explicit host/asset allow rules (`default_action: escalate` + scoped `allow`)
- Update `configs/example_org.yaml` with allowlist posture (asset-group allow under escalate default)
- Update `confirmed_malicious_sequence` and harness auto_contain paths with explicit allow configuration
- Walkthrough notebook: inject explicit host allow for Case 1; fix stale `org_config_refs`
- `tests/policy/conftest.py` allowlist helper (not `default_action=auto_contain`)
- Gate regression test: no matching rule → escalate at PolicyGate
- Re-pin `EXAMPLE_SNAPSHOT_HASH`

### Out of scope

- `docs/` edits (task lists `operator_runbook.md`; gap logged in review)
- `gate.py` logic changes (already consumes policy evaluation from V2-006/V2-012)
- V2-014+ correlator / target ownership

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | No matching scoped rule applies `default_action` (escalate), not implicit ALLOW |
| REQ-002 | Eval/walkthrough auto_contain paths use explicit allow rules, not permissive `default_action=auto_contain` |
| REQ-003 | Example org demonstrates escalate-by-default + scoped allow posture |
| REQ-004 | Regression: no-rule target escalates at PolicyGate |
| REQ-005 | Phase 3 gate / harness green with new posture |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Existing `test_default_action_applies_when_no_rule_matches` + new gate test |
| AC-002 | REQ-002 | Harness uses `_allowlist_containment_policy`; scenarios declare `containment_allow` where needed |
| AC-003 | REQ-003 | `example_org.yaml` has scoped allow rule; hash pinned |
| AC-004 | REQ-004 | `test_no_matching_rule_escalates_at_gate` passes |
| AC-005 | REQ-005 | Full pytest + phase3 gate + walkthrough check |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Allowlist policy helpers in harness + conftest | `evals/harness.py`, `tests/policy/conftest.py` | pending |
| T-002 | Example org allowlist posture + hash | `configs/example_org.yaml`, `tests/config/shared.py` | pending |
| T-003 | Scenario + phase3 gate updates | `evals/scenarios/`, `evals/run_phase3_gate.py` | pending |
| T-004 | Walkthrough notebook explicit allow | `notebooks/praetor_walkthrough.ipynb` | pending |
| T-005 | Gate regression test | `tests/policy/test_policy_gate.py` | pending |

## Risks

- Walkthrough committed outputs must be re-executed (CI runs nbconvert).
- `EXAMPLE_SNAPSHOT_HASH` cascade across engine/ticket tests.
