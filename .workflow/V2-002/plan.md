# Workflow Plan — V2-002 Host Corroboration Contract

## Goal

Ratify host + account corroboration as a first-class authorization concept, pin `insufficient_corroboration` in the Outcome Matrix, and classify Windows provenance paths (attacker-controllable vs not) before PolicyGate code changes (V2-011).

## Scope

### In scope

- **DEC-059** in `docs/decisions.md` — corroboration semantics, provenance classification, host vs account fault-flag split.
- `docs/contracts.md` — §12a corroboration contract + §13 Outcome Matrix row for `insufficient_corroboration`.
- `docs/proposals/v2_hardening.md` Item 1 ratified.
- `docs/proposals/delivery_backlog.md` — P0/P1 corroboration rows resolved / unblocked.
- Memory Bank updates.
- Flight Recorder artifacts.

### Out of scope

- Production code (`gate.py`, `provenance.py`, enum, harness scenario) — V2-011.
- `docs/spec.md` amendments — frozen until spec unfreeze.
- Account corroboration behavior changes — v1 `ambiguous_target_identity` path preserved.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Promote corroboration from account-only to host + account authorization concept. |
| REQ-002 | Ratify `insufficient_corroboration` as policy/safety fault flag with `system_fault_escalation=false`. |
| REQ-003 | Define attacker-controllable provenance classifications for v1 Windows sources. |
| REQ-004 | Define default classification for future normalizers (fail-closed). |
| REQ-005 | Document host vs account fault-flag mapping (`insufficient_corroboration` vs `ambiguous_target_identity`). |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `docs/contracts.md` §12a defines symmetric host + account corroboration rules. |
| AC-002 | REQ-002 | §13 Outcome Matrix row: host insufficient cited evidence → `escalate` / `insufficient_corroboration` / `false`. |
| AC-003 | REQ-003 | DEC-059 + §12a classify `sysmon_event_log` attacker-controllable, `windows_security_log` not. |
| AC-004 | REQ-004 | DEC-059 states new `provenance_path` values default attacker-controllable until contracts update. |
| AC-005 | REQ-005 | DEC-059 preserves account `ambiguous_target_identity`; host uses `insufficient_corroboration`. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| T-001 | Draft DEC-059 decision text | `docs/decisions.md` | pending |
| T-002 | Add §12a + §13 matrix row | `docs/contracts.md` | pending |
| T-003 | Ratify v2_hardening Item 1 | `docs/proposals/v2_hardening.md` | pending |
| T-004 | Unblock delivery backlog rows | `docs/proposals/delivery_backlog.md` | pending |
| T-005 | Update Memory Bank | `memory-bank/*` | pending |
| T-006 | Verification + flight recorder close | `.workflow/V2-002/*` | pending |

## Decision summary (owner ratification)

1. **Corroboration is first-class** for both host and account `auto_contain` authorization — not an account-only afterthought.
2. **Host floor (V2-011):** cited facts for host containment must span ≥2 distinct `provenance_path` values with ≥1 non-attacker-controllable; a sole cited fact with `ambiguity_flag=true` cannot authorize host containment.
3. **Account path unchanged:** SID present but uncorroborated still escalates `ambiguous_target_identity`.
4. **Provenance classification (v1 Windows):** `sysmon_event_log` = attacker-controllable; `windows_security_log` = non-attacker-controllable.
5. **Future normalizers:** new `provenance_path` values default **attacker-controllable** until explicitly classified in `docs/contracts.md` §12a (fail-closed).
6. **Outcome Matrix:** `insufficient_corroboration` — policy/safety class, `system_fault_escalation=false`. Enum/harness wiring deferred to V2-011.
