# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-052 | TASK-031 | `gate.py`, `run_phase3_gate.py` | `test_uncited_cross_host_noise_does_not_capture_target`, `test_noisy_bundle_consumes_task28_correlation_output` | intake via policy gate only (not TASK-028a intake CLI) | partial |
| REQ-002 | AC-002 | DEC-052 | TASK-031 | `noisy_correlated_real_telemetry.yaml` | `test_window_excludes_out_of_window_record_9999`, `test_noisy_correlation_gate_passes_on_healthy_tree` | REVIEW-004 xfail | complete |
| REQ-003 | AC-003 | DEC-052 | TASK-031 | `containment_policy.py`, `gate.py` | `test_citation_anchored_host_targeting.py`, `test_phase2_safety_targets_incident_host_not_noise_host` | REVIEW-004 | complete |
| REQ-004 | AC-004 | — | TASK-031 | `run_phase3_gate.py` | `test_gate_fails_when_expected_file_absent` | REVIEW-001 | complete |
| REQ-005 | AC-005 | DEC-052 | TASK-031 | `run_phase3_gate.py`, `multi_host_target_ambiguity.yaml` | `test_multi_cited_hosts_escalates_ambiguous_containment_target`, `test_account_containment_requires_identity_compliance` | REVIEW-001 | complete |
