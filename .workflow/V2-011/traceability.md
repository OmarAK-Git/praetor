# Traceability — V2-011

| Req | AC | Decision / Contract | Impl | Tests | Status |
|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-059, contracts §12a/§13 | `gate.py`, `provenance.py` | `test_host_single_provenance_escalates` | pending |
| REQ-002 | AC-002 | DEC-059 provenance trust table | `provenance.py` | `test_host_sysmon_security_corroboration_passes` | pending |
| REQ-003 | AC-003 | contracts §12a rule 3 | `provenance.py` | `test_sole_ambiguous_cited_fact_escalates` | pending |
| REQ-004 | AC-004 | PE-0029 account path | unchanged account branch | existing account policy tests | pending |
| REQ-005 | AC-005 | AG-0068 completeness guard | `evals/scenarios/insufficient_corroboration.yaml` | harness + `test_outcome_matrix_completeness_guard` | pending |
