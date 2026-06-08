# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-001, TASK-002 | `src/praetor/evidence/citations.py` | VERIFY-001 | REVIEW-001 | complete |
| REQ-002 | AC-002, AC-003 | DEC-001 | TASK-001, TASK-002 | `src/praetor/evidence/citations.py` | VERIFY-001 | REVIEW-001 | complete |
| REQ-003 | AC-004, AC-005 | DEC-002 | TASK-001, TASK-002 | `src/praetor/evidence/citations.py` | VERIFY-001 | REVIEW-001 | complete |
| REQ-004 | AC-006 | DEC-003 | TASK-001, TASK-002 | `src/praetor/evidence/citations.py` | VERIFY-001 | REVIEW-001 | complete |
| REQ-005 | AC-007 | DEC-004 | TASK-002, TASK-003 | `src/praetor/evidence/citations.py`, `src/praetor/engine/citations.py` | VERIFY-001, VERIFY-002 | REVIEW-002 | complete |
| REQ-006 | AC-008 | DEC-005 | TASK-003 | `src/praetor/engine/orchestrator.py`, `src/praetor/engine/skeleton.py` | VERIFY-002, VERIFY-003 | REVIEW-003 | complete |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Return a structured validation result instead of only `bool`. | Future PolicyGate and identity checks need resolved metadata, while intake can still consume `.valid`. |
| DEC-002 | Require at least one citation only for proposed `escalate` and `auto_contain`. | TASK-015 specifically names those dispositions; standard-review absence is not broadened beyond the task. |
| DEC-003 | Surface `ambiguity_flag` on each resolved citation. | TASK-015 requires ambiguity visibility for later identity decisions without implementing TASK-016. |
| DEC-004 | Validate against `EvidenceBundle` and adapt the skeleton fixture into that shape. | `EvidenceBundle` is the Task 2 contract and avoids keeping a bespoke engine-only validator. |
| DEC-005 | Preserve existing `invalid_model_citation` Outcome Matrix mapping in intake. | The docs require unresolved citations to escalate with `system_fault_escalation=true`. |
