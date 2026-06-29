# Workflow Plan — V2-012 Default Action Primitive

## Goal

Add required deployment-configurable `default_action` on `ContainmentPolicy` (DEC-058): schema, preflight, policy-layer fallback when no scoped rule matches, and example org config using the primitive instead of a catch-all rule.

## Scope

### In scope

- `default_action` field on `ContainmentPolicy` (typed `allow|deny|escalate|auto_contain`)
- Preflight rejects missing/invalid `default_action`; allow empty `rules` when `default_action` is set
- `evaluate_target_containment_policy` applies `default_action` when no rule matches (replaces implicit ALLOW for no-match)
- `configs/example_org.yaml` uses `default_action: escalate` (no catch-all rule)
- Config + policy unit tests; update `EXAMPLE_SNAPSHOT_HASH` and all `ContainmentPolicy` constructions

### Out of scope

- Eval harness / walkthrough posture flip (V2-013)
- Gate-layer changes beyond existing policy evaluation (V2-013)
- `docs/` edits
- Deprecating catch-all rules in `rules` (still valid for backward compat)

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Org config accepts typed required `default_action` |
| REQ-002 | Invalid/missing `default_action` fails preflight |
| REQ-003 | Scoped rule matches override `default_action` |
| REQ-004 | No matching rule applies `default_action` (not implicit ALLOW) |
| REQ-005 | Example org expresses escalate-by-default without catch-all rule |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `ContainmentPolicy.model_validate` accepts `default_action`; example org loads |
| AC-002 | REQ-002 | Preflight codes for missing/invalid `default_action` |
| AC-003 | REQ-003 | Policy test: scoped `allow` on ws-01 permits; other hosts get default escalate |
| AC-004 | REQ-004 | Policy test: empty rules + `default_action: escalate` blocks containment |
| AC-005 | REQ-005 | `example_org.yaml` has `default_action`, no catch-all rule; hash pinned |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Schema: `default_action`, optional empty rules | `org_config_sections.py` | pending |
| T-002 | Preflight validation | `preflight.py` | pending |
| T-003 | Policy fallback to `default_action` | `containment_policy.py` | pending |
| T-004 | Example org + sweep template | `example_org.yaml`, `codification/sweep.py` | pending |
| T-005 | Tests + hash pin | `tests/config/`, `tests/policy/`, fixtures | pending |

## Risks

- `EXAMPLE_SNAPSHOT_HASH` drift across many tests — recompute and pin once.
- Catch-all rules in tests still work; permissive helpers migrate to `default_action`.
