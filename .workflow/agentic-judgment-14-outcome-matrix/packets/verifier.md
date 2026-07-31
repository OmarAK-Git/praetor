# Fresh-Context Verification Packet — agentic-judgment-14-outcome-matrix

## Goal

Verify Outcome Matrix registration for `agentic_evidence_gathering_failed`, orchestrator routing via `_finish_system_fault` (no provider-health breaker trip), optional `DecisionEdict.session_trace_hash` pass-through from `ModelJudgment`, harness completeness coverage, DEC-064 documentation, and committed schema export for `session_trace_hash` — without PolicyGate evaluation changes.

## Acceptance checklist

- [ ] `OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED` registered in `src/praetor/metrics/events.py`
- [ ] `OUTCOME_MATRIX_SFE[AGENTIC_EVIDENCE_GATHERING_FAILED] = True` in `src/praetor/contracts/fault_flags.py`
- [ ] `process_alert_intake` catches `AgenticEvidenceGatheringFailedError` and calls `_finish_system_fault` (not `_finish_provider_fault`)
- [ ] Agentic gathering failure does **not** increment `production_failure_total` / trip provider-health breaker
- [ ] `AGENTIC_EVIDENCE_GATHERING_FAILED` is **not** in `LLM_FAILURE_FAULT_FLAGS`
- [ ] `DecisionEdict.session_trace_hash: str | None = None` added; `build_decision_edict` copies from `ModelJudgment.session_trace_hash`
- [ ] `FakeProviderMode.AGENTIC_EVIDENCE_GATHERING_FAILED` raises `AgenticEvidenceGatheringFailedError`; other FakeProvider modes unchanged
- [ ] `evals/scenarios/agentic_evidence_gathering_failed.yaml` present; scenario metrics use `llm_failure_by_fault_flag: {}` (not LLM failure metric)
- [ ] `test_outcome_matrix_completeness_guard` passes (all escalate-producing flags covered)
- [ ] DEC-064 in `docs/decisions.md`; §13 row + `DOMAIN_SESSION_TRACE` in `docs/contracts.md`; agentic package in `docs/architecture.md`
- [ ] DEC-064 states `org_config_section` and `similar_cases` are **not** corroboration-eligible
- [ ] `src/praetor/policy/` evaluation files show zero semantic diffs vs base
- [ ] Vertex / single-shot provider paths unchanged (no `vertex_provider.py` diff)
- [ ] Committed schemas: only `schemas/model_judgment.json` and `schemas/decision_edict.json` add optional `session_trace_hash`; `schemas/policy_gate_result.json` unchanged
- [ ] `python tools/schema_export.py --check` exits 0; `test_committed_schemas_match_export` passes

## Changed paths

- `src/praetor/metrics/events.py`
- `src/praetor/contracts/fault_flags.py`
- `src/praetor/contracts/edict.py`
- `src/praetor/engine/orchestrator.py`
- `src/praetor/engine/edict.py`
- `src/praetor/judgment/fake_provider.py`
- `evals/scenarios/agentic_evidence_gathering_failed.yaml`
- `docs/decisions.md`
- `docs/contracts.md`
- `docs/architecture.md`
- `schemas/model_judgment.json`
- `schemas/decision_edict.json`
- `tests/engine/test_agentic_evidence_gathering_failed_intake.py`
- `tests/contracts/test_edict_session_trace_hash.py`
- `tests/engine/test_engine_ids.py` (session_trace_hash pass-through test)

Implementation result: `results/implementer-result.md`  
Code review: `results/code-review.md` (**PASS**; remediation **PASS**)

## Run (read-only verification)

Set `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`, then:

```bash
pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py tests/evals/test_eval_harness.py tests/contracts/test_edict_session_trace_hash.py tests/engine/test_engine_ids.py::test_build_decision_edict_copies_session_trace_hash_from_judgment -q
pytest tests/evals/test_eval_harness.py::test_outcome_matrix_completeness_guard -q
pytest tests/evals/test_eval_harness.py::test_harness_all_scenarios_pass -q
ruff check src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine src/praetor/judgment/fake_provider.py evals tests/engine/test_agentic_evidence_gathering_failed_intake.py
mypy src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine/orchestrator.py src/praetor/judgment/fake_provider.py
python tools/schema_export.py --check
pytest tests/contracts/test_scope_guard.py::test_committed_schemas_match_export tests/contracts/test_scope_guard.py::test_schema_export_cli_check_passes -q
```

## Manual checks

1. Read `orchestrator.py` — confirm `AgenticEvidenceGatheringFailedError` handler calls `_finish_system_fault` without `in_transaction_hook` or `record_provider_breaker_metrics=True`.
2. Read `_record_intake_metrics_bypass_gate` — confirm `record_llm_failure` gated by `is_llm_failure_fault_flag`.
3. Compare `evals/scenarios/agentic_evidence_gathering_failed.yaml` metrics block to `correlation_failure.yaml` / `config_over_budget.yaml` (non-LLM SFE faults).
4. `git diff -- src/praetor/policy/` — expect no semantic changes.
5. `git diff -- src/praetor/judgment/vertex_provider.py` — expect no changes.
6. Grep `docs/decisions.md` DEC-064 for explicit exclusion of `org_config_section` from corroboration eligibility.
7. `git diff HEAD --ignore-cr-at-eol -- schemas/` — expect content changes only in `model_judgment.json` and `decision_edict.json` (both add optional `session_trace_hash`); `policy_gate_result.json` must have no content diff.
8. Confirm `session_trace_hash` appears nowhere else under `schemas/` except those two files.

Treat prior claims as unevidenced until you run commands and read the diff. Remain read-only except for `results/verifier-result.md`.
