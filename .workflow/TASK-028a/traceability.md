# Traceability: TASK-028a

| Req | AC | Decision | Task | Implementation | Test | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-048 | TASK-028a | `engine/orchestrator.py` → `evaluate_policy_gate` | `test_orchestrator_references_evaluate_policy_gate` | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-028 | TASK-028a | PolicyGate on intake path | `test_intake_emits_auto_contain_when_gate_approves`, eval scenario | REVIEW-001 | pass |
| REQ-003 | AC-003 | — | TASK-028a | host bundle dc-01 + gate | `test_intake_escalates_never_contain_snapshot_when_target_excluded`, eval scenario | — | pass |
| REQ-004 | AC-004 | DEC-044 | TASK-028a | `MetricsCollector` param on intake | `tests/metrics/test_orchestrator_metrics.py` | — | pass |
| REQ-005 | AC-005 | DEC-048 | TASK-028a | Remove xfail markers | tripwire module | — | pass |
| REQ-006 | AC-006 | — | TASK-028a | `evals/scenarios/*.yaml` runner | `python -m evals.harness` | — | pass |
