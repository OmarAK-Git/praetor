# Workflow Plan — V2-006 Escalate Rule Blocks Containment

## Goal

Implement DEC-058 rule-action semantics: sole matching `escalate` or `deny` rules block `auto_contain` at the policy layer with distinct fault flags; unresolved permit+block conflicts emit `policy_ambiguity`.

## Scope

### In scope

- `PolicyAction.ESCALATE` and distinct fault flags `containment_policy_denied`, `containment_policy_escalation_required`.
- `evaluate_target_containment_policy` blocking semantics per DEC-058 §Rule action semantics.
- `gate.py` maps deny/escalate policy results to distinct escalate outcomes.
- `OutcomeMatrixFaultFlag` + `evals/outcome_matrix.py` entries (provisional names per DEC-058).
- Unit tests in `tests/policy/test_containment_policy.py` and gate tests in `tests/policy/test_policy_gate.py`.
- Minimal test fixture updates where example org's catch-all `escalate` rule now correctly blocks containment.

### Out of scope

- `default_action` schema and preflight (V2-012).
- Implicit ALLOW removal when no rule matches (V2-013).
- Precedence resolution implementation beyond existing conflict→ambiguity when precedence absent.
- `docs/` changes (hard limit).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Target matched only by `action: escalate` cannot reach `auto_contain`. |
| REQ-002 | `deny` and `escalate` produce distinct policy-layer results and fault flags. |
| REQ-003 | `auto_contain` + unresolved `escalate`/`deny` conflict produces `policy_ambiguity`. |
| REQ-004 | Gate maps policy deny/escalate blocks to escalate with correct fault flags (`system_fault_escalation=false`). |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Unit + gate tests: sole escalate rule → escalate, not auto_contain. |
| AC-002 | REQ-002 | Unit + gate tests: sole deny vs sole escalate yield different `fault_flag` values. |
| AC-003 | REQ-003 | Existing conflict test remains green with `policy_ambiguity`. |
| AC-004 | REQ-004 | Gate integration tests assert distinct fault flags for deny vs escalate blocks. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Add fault flag constants + PolicyAction.ESCALATE | `containment_policy.py`, `metrics/events.py`, `evals/outcome_matrix.py` | pending |
| T-002 | Policy evaluation blocking logic | `containment_policy.py` | pending |
| T-003 | Gate mapping for deny/escalate blocks | `gate.py` | pending |
| T-004 | Policy unit tests (TDD) | `tests/policy/test_containment_policy.py` | pending |
| T-005 | Gate tests + permissive fixture helper | `tests/policy/conftest.py`, `tests/policy/test_policy_gate.py` | pending |
| T-006 | Fix downstream policy tests using default snapshot | `test_citation_anchored_host_targeting.py`, `test_directive_embedded_hash.py`, etc. | pending |
| T-007 | Verification + flight recorder | `.workflow/V2-006/*`, `memory-bank/*` | pending |

## Decision alignment

- **DEC-058 (V2-001):** `escalate` is not hint-only; deny vs escalate distinction required for audit.
- **V2-012/V2-013:** No-rule fallthrough and `default_action` deferred.
