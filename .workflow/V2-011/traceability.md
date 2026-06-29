# Traceability — V2-011

| Req | AC | Decision / Contract | Impl | Tests | Status |
|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-059, contracts §12a/§13 | `gate.py`, `provenance.py` | `test_host_single_cited_provenance_escalates` | pass |
| REQ-002 | AC-002 | DEC-059 provenance trust table | `provenance.py` | `test_host_sysmon_security_citations_auto_contain`, `test_sysmon_plus_security_same_host_passes` | pass |
| REQ-002a | AC-002 | contracts §12a host-anchoring cites | `provenance.py` `_cited_fact_anchors_host` | `test_unrelated_security_cite_does_not_corroborate_host_target`, `test_security_without_host_id_does_not_corroborate_target` | pass |
| REQ-003 | AC-003 | contracts §12a rule 3 | `provenance.py` | `test_sole_ambiguous_cited_fact_escalates` | pass |
| REQ-004 | AC-004 | PE-0029 account path | unchanged account branch | `test_account_path_unaffected_by_host_corroboration_flag` | pass |
| REQ-005 | AC-005 | AG-0068 completeness guard | `evals/scenarios/insufficient_corroboration.yaml` | harness + `test_outcome_matrix_completeness_guard` | pass |
