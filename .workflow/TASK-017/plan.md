# Workflow Plan

## Goal

Implement TASK-017: Deterministic PolicyGate v1 with startup recovery step 6 and production singleton entrypoint.

## Scope

### In scope

- `praetor.policy.gate` — deterministic PolicyGate with Outcome Matrix enforcement
- `praetor.policy.containment_policy` — target resolution and policy ambiguity
- `praetor.policy.directive_builder` — ContainmentDirective construction
- `praetor.policy.state` — rate counters, breakers, startup reconciliation (step 6)
- `praetor.runtime.startup.open_production_state_store`
- Startup recovery step 6 in `run_engine_startup_recovery`
- Tests under `tests/policy/`

### Out of scope

- Engine orchestrator wiring (PolicyGate callable; skeleton inline policy unchanged)
- Task 18 full transactional rate limits / containment breaker
- Task 19 provider-health breaker
- Docs changes

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Invalid evidence citation → `escalate(invalid_model_citation)` |
| REQ-002 | Snapshot never-contain → `escalate(never_contain_snapshot)` |
| REQ-003 | Live never-contain / emergency → `escalate(never_contain_live_conflict)` |
| REQ-004 | Active emergency visible in live never-contain evaluation |
| REQ-005 | Insufficient account corroboration → `escalate(ambiguous_target_identity)` |
| REQ-006 | Account feature gate false → `escalate(account_containment_disabled)` |
| REQ-007 | Account auto-contain when feature gate enabled and identity passes |
| REQ-008 | Target-scoped policy conflict → `escalate(policy_ambiguity)` |
| REQ-009 | Rate limit exceeded → `escalate(rate_limit_exceeded)` |
| REQ-010 | Duplicate idempotency key suppresses new directive emission |
| REQ-011 | Expired directive permits fresh re-issue (same idempotency key, no supersession) |
| REQ-012 | Feed unhealthy / SLO breach → `escalate(revocation_feed_unhealthy)` |
| REQ-013 | Auto-contain side effects in one `critical_transaction` |
| REQ-014 | `proposed_disposition` and `final_disposition` recorded separately |
| REQ-015 | Startup recovery step 6 reconciles policy state |
| REQ-016 | Production entrypoint requires held `SingletonLock` |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–014 | `tests/policy/test_policy_gate.py` pass |
| AC-002 | REQ-008 | `tests/policy/test_containment_policy.py` pass |
| AC-003 | REQ-015 | `run_engine_startup_recovery` calls `reconcile_policy_state` |
| AC-004 | REQ-016 | Production entrypoint tests pass |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Policy state schema + step 6 reconciliation | `policy/state.py`, `engine/recovery.py` | complete |
| T-002 | Containment policy + directive builder | `policy/containment_policy.py`, `policy/directive_builder.py` | complete |
| T-003 | PolicyGate core | `policy/gate.py`, `policy/identity.py` | complete |
| T-004 | Production startup + tests | `runtime/startup.py`, `tests/policy/*` | complete |
| T-005 | Verification + Memory Bank | `.workflow/TASK-017/*`, `memory-bank/*` | complete |

## Risks

- v1 rate-limit ceiling is fixed (`_V1_DEFAULT_SCOPE_LIMIT=1`) until Task 18 org-config limits land.
- Engine still uses skeleton inline policy; PolicyGate integration deferred to a follow-on wiring task.
- After expired-directive fresh re-issue, the prior expired row (`revoked=0`) remains in `outstanding_containment_directives` alongside the new row sharing the same idempotency key. Duplicate suppression filters by expiry so behavior is correct; whether startup step 6/7 should purge expired-unrevoked rows is **undecided** (flag only).

## Follow-on: PolicyGate engine wiring (hard acceptance)

When the orchestrator replaces skeleton inline policy with `evaluate_policy_gate`, the following is **in scope and not deferrable**:

- PolicyGate stops opening its own `critical_transaction` and returns a fully-specified emit decision (directive to persist, idempotency/rate writes, evaluated snapshot content).
- The engine opens **one** serializable `critical_transaction` over directive persistence + idempotency + rate counter + `DecisionEdict` + `NeverContainSnapshotRecord`, using the exact live never-contain list the gate evaluated.
- Deferring this split **is** the directive-without-audit-record contradictory-state crash window (`spec.md` § DecisionEdict / never-contain snapshot pairing).

Until wiring lands, gate.py retains its internal transaction so policy tests stay isolated (TASK-017).
