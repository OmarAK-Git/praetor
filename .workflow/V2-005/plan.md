# Workflow Plan — V2-005 Strict ContainmentRule Schema and Scope Preflight

## Goal

Close the silent containment-rule scope drop (v2_hardening Item 2a): typed `scope` on `ContainmentRule`, `extra="forbid"` on containment models, preflight rejects malformed scopes with a clear code, and the example org config uses a valid catch-all scope shape. Policy-layer default-allow and `default_action` are **out of scope** (V2-012/V2-013).

## Scope

### In scope

- Typed `ContainmentRule.scope` union: target (`target_type` + `target_id`), asset (`asset_id`), catch-all (`catch_all: true`).
- `extra="forbid"` on `ContainmentRule` and `ContainmentPolicy`; typed `action` literal.
- Preflight rejects string scopes (e.g. `scope: global`) with `invalid_containment_rule_scope`.
- Preflight/schema rejects unknown rule keys and invalid scope shapes before activation.
- Gate evaluates catch-all scopes (no silent skip of valid declared rules).
- `configs/example_org.yaml` updated to `{ catch_all: true }`; `EXAMPLE_SNAPSHOT_HASH` refreshed.
- Tests in `tests/config/test_org_config_loader.py` and `tests/config/test_config_gate.py`.

### Out of scope

- `default_action` schema and required-field preflight (V2-012).
- `escalate`/`deny` blocking containment at policy layer (V2-006).
- Posture flip / implicit ALLOW removal (V2-013).
- `docs/` changes (hard limit).
- `codification/sweep.py` template (proposed artifacts non-activatable; follow-on hygiene).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | `scope: global` (string) fails preflight with code `invalid_containment_rule_scope`. |
| REQ-002 | Unknown keys on `ContainmentRule` / `ContainmentPolicy` fail validation. |
| REQ-003 | Valid target, asset, and catch-all scopes round-trip through `OrgConfigSnapshot`. |
| REQ-004 | Example config activates via preflight with valid containment rule scope. |
| REQ-005 | Valid declared rule scopes are not silently skipped at gate evaluation. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Test asserts `invalid_containment_rule_scope` for string scope. |
| AC-002 | REQ-002 | Tests assert extra-key rejection on rule and policy models + preflight. |
| AC-003 | REQ-003 | Round-trip tests for three scope shapes pass preflight and snapshot build. |
| AC-004 | REQ-004 | `test_valid_config_loads_stable_snapshot_hash` green with updated example YAML. |
| AC-005 | REQ-005 | `evaluate_target_containment_policy` matches `catch_all` rules (unit coverage). |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Scope models + strict ContainmentRule/Policy | `org_config_sections.py` | pending |
| T-002 | Preflight scope validation | `preflight.py` | pending |
| T-003 | Gate catch-all matching | `containment_policy.py` | pending |
| T-004 | Example config + snapshot hash | `configs/example_org.yaml`, `tests/config/shared.py` | pending |
| T-005 | Config tests | `tests/config/test_org_config_loader.py`, `test_config_gate.py` | pending |
| T-006 | Fix policy tests with invalid scopes | `tests/policy/test_rate_limits.py`, `test_containment_circuit_breaker.py` | pending |
| T-007 | Verification + flight recorder | `.workflow/V2-005/*`, `memory-bank/*` | pending |

## Decision alignment

- **DEC-058 (V2-001):** 2a validation hardening only; `default_action` deferred to V2-012.
- **Catch-all scope:** `{ catch_all: true }` replaces invalid `scope: global` string until `default_action` lands.
