# Review: TASK-025

## Status

complete

## Notes

- Annotations stored in `analyst_annotations` table, not ledger hash chain — edict immutability by design.
- `decision_id` linkage is store metadata; `AnalystAnnotation` contract unchanged (Task 2).
- Decision existence checks both `completed_decisions` and ledger `decision_edict` rows (json_extract).
- `submit_annotation` requires open critical transaction; auth reuses Task 4 surfaces.

## Gaps

- Annotation schema wired in `open_state_store`; no intake/UI surface for submission.
- No HTTP/API surface; Python callable only per Task 4 pattern.
