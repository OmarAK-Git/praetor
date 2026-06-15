# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-001 | orchestrator lazy import | `test_real_sysmon_process_creation_provenance_path` | REVIEW-001 | complete |
| REQ-002 | AC-002 | DEC-001 | TASK-001 | orchestrator lazy import | `test_real_security_logon_provenance_path` | REVIEW-001 | complete |
| REQ-003 | AC-003 | DEC-002 | TASK-001 | — | `test_correlated_real_pair_*`, `test_real_correlated_bundle_account_*` | REVIEW-004 | complete |
| REQ-004 | AC-004 | DEC-002 | TASK-001 | — | `test_two_sysmon_facts_*`, `test_real_sysmon_only_*` | REVIEW-002 | complete |
| REQ-005 | AC-005 | DEC-004 | TASK-001 | — | `test_ambiguous_sysmon_*`, `test_corroborated_ambiguous_identity_*` | REVIEW-003 | complete |
| REQ-006 | AC-006 | DEC-002 | TASK-001 | — | `test_real_eligible_pair_*`, `test_real_sysmon_only_*` | REVIEW-001 | complete |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Use committed `tests/fixtures/sysmon` and `tests/fixtures/security` as "real" telemetry shapes. | TASK-028 fixtures; OTRF download is TASK-030 scope. |
| DEC-002 | Reuse TASK-016 corroboration/eligibility oracles; assert production via `evaluate_policy_gate`. | Done-when: real shapes gate production account containment readiness. |
| DEC-003 | No `pytest.mark.integration` on local fixture tests; they run in default CI (`pytest -q`). | Integration marker = external services/credentials per `pyproject.toml`. |
| DEC-004 | spec.md:309 conjunction: ambiguity + insufficient corroboration → escalate; sufficient corroboration → account eligible despite fact-level ambiguity. | No `identity.py` change; test pins AUTO_CONTAIN when gate enabled. |
