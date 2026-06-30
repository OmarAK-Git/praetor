# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | AG-0080 | V2-014 | `correlation/host_isolation.py`, `correlation/__init__.py` | `test_correlator_should_drop_cross_host_in_window_noise`, `test_host_isolation.py` | — | pending |
| REQ-002 | AC-002 | AG-0079 | V2-014 | `evals/correlation_expected/*.yaml` | `test_correlation_gate.py`, `test_phase3_regression_gate.py` | — | pending |
| REQ-003 | AC-003 | TASK-030 | V2-014 | `correlation/window.py` (unchanged) | `test_window_excludes_out_of_window_record_9999` | — | pending |
| REQ-004 | AC-004 | DEC-052 | V2-014 | policy layer unchanged | `test_citation_anchored_host_targeting.py` | — | pending |
| REQ-005 | AC-005 | — | V2-014 | — | pytest, `evals.correlation_gate`, `evals.run_phase3_gate` | — | pending |
