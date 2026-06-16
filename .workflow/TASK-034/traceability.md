# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001, DEC-004 | TASK-002 | `src/praetor/codification/sweep.py` | `test_sweep_summarizes_observations_from_fixtures` | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-002 | TASK-002 | `sweep.py`, `config/preflight.py` | `test_proposed_artifact_rejected_by_preflight` | REVIEW-001 | pass |
| REQ-003 | AC-003 | DEC-001 | TASK-002 | `src/praetor/codification/report.py` | `test_report_documents_coverage_limits` | REVIEW-001 | pass |
| REQ-004 | AC-004 | DEC-003 | TASK-002 | `report.py` | `test_report_documents_absence_of_evidence_risks` | REVIEW-001 | pass |
| REQ-005 | AC-005 | DEC-002, DEC-003 | TASK-002 | `sweep.py`, `report.py` | `test_sweep_exposes_reviewable_artifact_and_report` | REVIEW-001 | pass |
