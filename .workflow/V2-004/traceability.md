# Traceability — V2-004

| REQ | AC | Decision | Task | Implementation | Test | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-061 | V2-004 | `docs/contracts.md` §13 | `rg provider_unavailable docs/contracts.md` | — | pass |
| REQ-002 | AC-002 | DEC-061 | V2-004 | `metrics/events.py`, `evals/outcome_matrix.py` | `test_outcome_matrix_completeness_guard` | — | pass |
| REQ-003 | AC-003 | DEC-061 | V2-004 | `LLM_FAILURE_FAULT_FLAGS` | `tests/evals/test_provider_unavailable_matrix.py` | — | pass |
| REQ-004 | AC-004 | DEC-061 | V2-004 | `evals/scenarios/provider_unavailable.yaml` | harness completeness + `test_harness_all_scenarios_pass` | — | pass |
| REQ-005 | AC-005 | DEC-061 | V2-004 | `orchestrator.py`, `fake_provider.py` | `test_provider_unavailable_escalates` | — | pass |
| REQ-006 | AC-006 | TASK-019 | — | `provider_health_breaker.py` (unchanged) | `test_provider_unavailable_trips_breaker` | — | pass |
