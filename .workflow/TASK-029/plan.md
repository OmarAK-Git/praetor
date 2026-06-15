# Workflow Plan: TASK-029

## Goal

Add correlator identity compliance tests proving real Sysmon/Security fixture normalization produces the same account corroboration and containment-eligibility outcomes as TASK-016 synthetic tests.

## Scope

### In scope

- Add `tests/correlation/test_correlator_identity_compliance.py`.
- Assert real Sysmon process-creation facts use `provenance_path=sysmon_event_log`.
- Assert real Security 4624 facts use `provenance_path=windows_security_log`.
- Assert correlated Sysmon+Security pair satisfies `meets_account_corroboration`.
- Assert two Sysmon-only facts from the same scenario fail corroboration.
- Assert `ambiguity_flag` on ambiguous real Sysmon fixtures and eligibility escalation when corroboration is insufficient.
- Parity checks against TASK-016 synthetic eligibility outcomes.

### Out of scope

- Correlation accuracy gate (TASK-030).
- Phase 3 harness (TASK-031).
- Source changes unless tests expose a defect.
- Modify `docs/`.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Real Sysmon process-creation fixture normalizes with `provenance_path=sysmon_event_log`. |
| REQ-002 | Real Windows Security 4624 fixture normalizes with `provenance_path=windows_security_log`. |
| REQ-003 | Correlated real Sysmon+Security pair satisfies account corroboration. |
| REQ-004 | Two Sysmon facts from the same scenario do not satisfy account corroboration. |
| REQ-005 | Ambiguous real Sysmon facts set `ambiguity_flag=true`; insufficient corroboration escalates. |
| REQ-006 | Real normalized eligibility outcomes match TASK-016 synthetic fixtures. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Test loads committed Sysmon fixture and asserts provenance on normalized fact. |
| AC-002 | REQ-002 | Test loads committed Security fixture and asserts provenance on normalized fact. |
| AC-003 | REQ-003 | Correlated bundle from real fixtures passes `meets_account_corroboration` and authorizes containment when SID-backed. |
| AC-004 | REQ-004 | Sysmon-only correlated bundle fails corroboration and escalates eligibility. |
| AC-005 | REQ-005 | Ambiguous Sysmon fixture sets flag; eligibility escalates without Security corroboration. |
| AC-006 | REQ-006 | Parametrized or explicit parity asserts same eligibility as synthetic fixtures. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing identity compliance tests (test-first). | `tests/correlation/test_correlator_identity_compliance.py`, `orchestrator.py` | complete |
| TASK-002 | Run verification suite and update workflow + Memory Bank. | `.workflow/TASK-029/*`, `memory-bank/*` | complete |

## Risks

- Plan wording "marked integration" applies to real telemetry fixture shapes; committed local fixtures run in default CI (same as TASK-028) — external OTRF download deferred to TASK-030.
- TASK-028 already covers some overlap; this file focuses on TASK-016 eligibility parity, not re-testing normalization mechanics.
