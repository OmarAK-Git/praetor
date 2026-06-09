# Workflow Plan

## Goal

Implement TASK-016: canonical account identity validation and synthetic provenance corroboration tests so account containment eligibility is testable before real correlation exists.

## Scope

### In scope

- Add `praetor.evidence.provenance` for provenance-path constants and account corroboration checks.
- Add `praetor.policy.identity` for SID-backed identity checks and account containment eligibility evaluation.
- Add synthetic JSON fixtures under `tests/fixtures/synthetic/`.
- Add focused tests in `tests/evidence/test_account_corroboration.py`.
- Update scope guard to allow the intentional `policy` package.

### Out of scope

- PolicyGate implementation (TASK-017).
- Real telemetry normalization / correlation (TASK-028+).
- Account production feature gate (`account_containment_disabled`) — TASK-017.
- Changes to source-of-truth docs.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Facts missing `provenance_path` fail schema validation. |
| REQ-002 | `CanonicalAccountIdentity` requires SID, domain, account name, account type, authority source, and ambiguity flag. |
| REQ-003 | SID-absent identity cannot authorize account containment. |
| REQ-004 | Same-provenance facts do not corroborate account containment. |
| REQ-005 | One `sysmon_event_log` plus one `windows_security_log` satisfies corroboration. |
| REQ-006 | Ambiguous target with insufficient corroboration produces `escalate(ambiguous_target_identity)`. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `EvidenceFact` validation rejects payloads without `provenance_path`. |
| AC-002 | REQ-002 | `CanonicalAccountIdentity` validation rejects payloads missing any required field. |
| AC-003 | REQ-003 | `evaluate_account_containment_eligibility` returns `authorized=False` for empty/absent SID. |
| AC-004 | REQ-004 | Two `sysmon_event_log` facts do not satisfy `meets_account_corroboration`. |
| AC-005 | REQ-005 | One sysmon and one windows security fact satisfy `meets_account_corroboration`. |
| AC-006 | REQ-006 | Ambiguous identity with insufficient corroboration yields `fault_flag=ambiguous_target_identity` and `system_fault_escalation=False`. |
| AC-007 | REQ-005 | Synthetic JSON fixtures load and drive corroboration tests. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing `tests/evidence/test_account_corroboration.py` and synthetic fixtures. | `tests/evidence/test_account_corroboration.py`, `tests/fixtures/synthetic/*.json` | complete |
| TASK-002 | Add provenance corroboration module. | `src/praetor/evidence/provenance.py`, `src/praetor/evidence/__init__.py` | complete |
| TASK-003 | Add policy identity eligibility module. | `src/praetor/policy/identity.py`, `src/praetor/policy/__init__.py` | complete |
| TASK-004 | Update scope guard for `policy` package. | `tests/contracts/test_scope_guard.py` | complete |
| TASK-005 | Run verification and update workflow reports / Memory Bank. | `.workflow/TASK-016/*`, `memory-bank/*` | complete |

## Risks

- Scope guard currently forbids `policy` package; must update intentionally like TASK-015 did for `evidence`.
- Corroboration rules are v1 Windows/Sysmon-specific; keep logic narrow to avoid over-generalizing beyond spec.
