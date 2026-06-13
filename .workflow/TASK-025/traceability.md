# Traceability Matrix: TASK-025

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | — | T-002 | `annotations/store.py` Pydantic build | `test_cross_field_*` | REVIEW-001 | pass |
| REQ-002 | AC-001 | TASK-004 reuse | T-002 | `verified_record_identity` | `test_reviewer_identity_*` | REVIEW-001 | pass |
| REQ-003 | AC-001 | — | T-002 | `decision_id_exists` | `test_unknown_decision_*`, `test_links_*` | REVIEW-001 | pass |
| REQ-004 | AC-001 | — | T-002 | separate `analyst_annotations` table | `test_edict_hash_unchanged` | REVIEW-001 | pass |
| REQ-005 | AC-001 | TASK-004 reuse | T-002 | `authenticate_annotation_submission` | `test_wrong_role_rejected` | REVIEW-001 | pass |
| AC-002 | AC-002 | — | T-003 | — | VERIFY-002–004 | REVIEW-001 | pass |
