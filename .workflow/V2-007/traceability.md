# Traceability Matrix — V2-007

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-061 | V2-007 | `orchestrator.py` ProviderUnavailable catch | `test_provider_unavailable_intake_escalates` | — | pass |
| REQ-002 | AC-002 | DEC-061 | V2-007 | `_finish_system_fault` | `assert_outcome_matrix_edict` in engine test | — | pass |
| REQ-003 | AC-003 | DEC-061 | V2-007 | `record_provider_production_failure_in_transaction` via intake hook | `test_provider_unavailable_records_breaker_production_failure` | — | pass |
| REQ-004 | AC-004 | DEC-061 | V2-007 | `_record_intake_metrics_bypass_gate` | `test_intake_records_provider_unavailable_llm_failure_metric` | — | pass |
