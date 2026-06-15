# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001, DEC-002 | TASK-001/002 | `evals/correlation_gate.py`, `evals/correlation_expected/otrf_process_chain_corroborated_logon.yaml` | `test_gate_passes_known_otrf_scenario` | REVIEW-001 | complete |
| REQ-002 | AC-002 | DEC-003 | TASK-001/002 | `evals/correlation_expected/otrf_noisy_in_window_bounded.yaml` | `test_gate_passes_noise_below_threshold`, `test_gate_fails_noise_above_threshold` | REVIEW-002 | complete |
| REQ-003 | AC-003 | DEC-002 | TASK-001/002 | `run_correlation_gate` relationship checks | `test_gate_fails_missing_process_relationship` | REVIEW-003 | complete |
| REQ-004 | AC-004 | DEC-004 | TASK-002 | `verify_fixture_manifest_checksums` | `test_manifest_checksum_verified_before_gate`, `test_gate_fails_on_manifest_mismatch` | REVIEW-004 | complete |
| REQ-005 | AC-005 | DEC-005 | TASK-002 | `evals/correlation_gate.main` | `test_correlation_gate_cli`, full pytest | REVIEW-005 | complete |
