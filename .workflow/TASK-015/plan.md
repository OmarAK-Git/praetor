# Workflow Plan

## Goal

Implement TASK-015: a shared structural evidence citation validator that checks `ModelJudgment.cited_evidence_refs` against real evidence IDs and field paths, exposes cited fact ambiguity, and preserves the existing `invalid_model_citation` escalation behavior.

## Scope

### In scope

- Add `praetor.evidence.citations` as the shared citation validation module.
- Validate cited evidence IDs and field paths against an `EvidenceBundle`.
- Treat empty citations as invalid for `escalate` and `auto_contain` proposed dispositions.
- Return resolved citation metadata, including `ambiguity_flag`, for future identity/PolicyGate consumers.
- Wire the walking-skeleton intake citation check to the shared validator.
- Add focused unit tests under `tests/evidence/` and keep existing engine/provider citation tests green.

### Out of scope

- PolicyGate implementation.
- Reasoning-quality validation.
- Org-config reference validation.
- Changes to source-of-truth docs.
- Future identity-gate behavior from TASK-016.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Valid cited evidence IDs and field paths resolve successfully. |
| REQ-002 | Invalid cited evidence IDs or field paths fail validation. |
| REQ-003 | Missing citations fail when the proposed disposition is `escalate` or `auto_contain`. |
| REQ-004 | Resolved citation metadata exposes the cited fact's `ambiguity_flag`. |
| REQ-005 | The shared validator is usable by current rationale validation and future PolicyGate checks without implementing PolicyGate. |
| REQ-006 | Existing intake behavior maps invalid model citations to `escalate(invalid_model_citation)` with `system_fault_escalation=true`. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | A judgment citing an existing evidence ID and normalized-field path returns a valid result with resolved citations. |
| AC-002 | REQ-002 | A judgment citing a missing evidence ID returns an invalid result with a machine-readable error. |
| AC-003 | REQ-002 | A judgment citing a missing field path on an existing fact returns an invalid result with a machine-readable error. |
| AC-004 | REQ-003 | Empty `cited_evidence_refs` fails for `Disposition.ESCALATE` and `Disposition.AUTO_CONTAIN`. |
| AC-005 | REQ-003 | Empty `cited_evidence_refs` remains structurally acceptable for `Disposition.STANDARD_REVIEW`. |
| AC-006 | REQ-004 | A resolved citation for an ambiguous fact exposes `ambiguity_flag=True`. |
| AC-007 | REQ-005 | The validator accepts a general `EvidenceBundle`; walking-skeleton code uses it through a shared path rather than bespoke ID-only validation. |
| AC-008 | REQ-006 | Existing engine/provider invalid citation tests still pass. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing `tests/evidence/test_citation_validation.py` tests for valid refs, invalid refs, required citations, and ambiguity metadata. | `tests/evidence/test_citation_validation.py` | complete |
| TASK-002 | Add shared evidence citation validator and package exports. | `src/praetor/evidence/citations.py`, `src/praetor/evidence/__init__.py` | complete |
| TASK-003 | Wire the walking skeleton validator to the shared module while preserving current intake escalation behavior. | `src/praetor/engine/citations.py`, `src/praetor/engine/orchestrator.py`, `src/praetor/engine/skeleton.py` | complete |
| TASK-004 | Run focused and full verification, then update workflow reports and Memory Bank. | `.workflow/TASK-015/*`, `memory-bank/*` | complete |
