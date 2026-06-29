# Workflow Plan — V2-001 Authorization Posture Decision

## Goal

Ratify V2 containment authorization posture, rule-action semantics, rule precedence, and `escalate`-blocks-containment behavior so V2-005/V2-006/V2-012/V2-013 can implement without open semantic questions.

## Scope

### In scope

- Owner decision recorded as **DEC-058** in `docs/decisions.md`.
- `docs/proposals/v2_hardening.md` Item 2 posture section updated (drift retired; 2b direction ratified).
- `docs/proposals/delivery_backlog.md` authorization posture rows marked resolved / unblocked.
- Memory Bank task status and context updates.
- Flight Recorder artifacts (plan, traceability, verification, review, final-report).

### Out of scope

- Code changes (`containment_policy.py`, schema, preflight, tests) — V2-005, V2-006, V2-012, V2-013.
- New Outcome Matrix rows / enum members — wired when V2-006 implements deny/escalate fault flags.
- `docs/spec.md` and `docs/contracts.md` amendments — deferred until implementation tasks pin rows.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Choose hard default-deny vs deployment-configurable `default_action`. |
| REQ-002 | Define `allow`, `deny`, `escalate`, and `auto_contain` rule-action semantics. |
| REQ-003 | Decide whether a sole matching `escalate` rule blocks containment. |
| REQ-004 | Formally retire v1 implicit default-allow as drift. |
| REQ-005 | Document rule precedence and `default_action` catch-all ordering. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | DEC-058 states deployment-configurable required `default_action`; no implicit ALLOW fallthrough. |
| AC-002 | REQ-002 | DEC-058 defines all four actions at the policy authorization layer. |
| AC-003 | REQ-003 | DEC-058 states sole `escalate` match blocks `auto_contain` (not hint-only). |
| AC-004 | REQ-004 | v2_hardening Item 2 marks v1 default-allow as retired drift. |
| AC-005 | REQ-005 | DEC-058 documents scoped-rule-first precedence and `default_action` as lowest. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Draft DEC-058 decision text | `docs/decisions.md` | complete |
| T-002 | Update v2_hardening Item 2 ratification | `docs/proposals/v2_hardening.md` | complete |
| T-003 | Unblock delivery backlog posture rows | `docs/proposals/delivery_backlog.md` | complete |
| T-004 | Update Memory Bank | `memory-bank/*` | complete |
| T-005 | Verification + flight recorder close | `.workflow/V2-001/*` | complete |

## Decision summary (owner ratification)

1. **Posture:** deployment-configurable `default_action` on `ContainmentPolicy` (required at activation in V2-012). Recommended safe default: `escalate`. Not a hard-coded engine denylist.
2. **Drift retired:** v1 `evaluate_target_containment_policy` implicit `ALLOW` when no rule matches is implementation drift, not product intent.
3. **Rule actions:** `allow` and `auto_contain` affirm containment at policy layer; `deny` and `escalate` block it; `escalate` is not hint-only.
4. **Precedence:** scoped rules first; conflicts → `policy_ambiguity` unless `precedence` resolves; no match → `default_action`.
