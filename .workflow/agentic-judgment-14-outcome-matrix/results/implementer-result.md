# Implementer result — agentic-judgment-14-outcome-matrix

## Summary

Registered `agentic_evidence_gathering_failed` Outcome Matrix row (DEC-064), wired orchestrator catch via `_finish_system_fault` (no breaker trip), added harness scenario + `FakeProviderMode`, threaded optional `session_trace_hash` through `DecisionEdict`, and updated docs.

## Files changed

| File | Rationale |
|---|---|
| `src/praetor/metrics/events.py` | Added `OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED` |
| `src/praetor/contracts/fault_flags.py` | `OUTCOME_MATRIX_SFE[...] = True` for new flag |
| `src/praetor/engine/orchestrator.py` | `except AgenticEvidenceGatheringFailedError` → `_finish_system_fault` |
| `src/praetor/judgment/fake_provider.py` | `FakeProviderMode.AGENTIC_EVIDENCE_GATHERING_FAILED` raises typed error |
| `src/praetor/contracts/edict.py` | Optional `DecisionEdict.session_trace_hash` field |
| `src/praetor/engine/edict.py` | Copy `session_trace_hash` from `ModelJudgment` in `build_decision_edict` |
| `evals/scenarios/agentic_evidence_gathering_failed.yaml` | Harness scenario for completeness guard |
| `docs/decisions.md` | DEC-064 index row + full section |
| `docs/contracts.md` | §13 Outcome Matrix row + `DOMAIN_SESSION_TRACE` / `compute_session_trace_hash` |
| `docs/architecture.md` | `praetor.judgment.agentic` package row |
| `tests/engine/test_agentic_evidence_gathering_failed_intake.py` | Intake escalation + breaker non-trip tests (TDD) |
| `tests/contracts/test_edict_session_trace_hash.py` | `ModelJudgment.session_trace_hash` contract tests |
| `tests/engine/test_engine_ids.py` | `build_decision_edict` pass-through test (plan alt to separate engine file) |

**Not changed:** `evals/harness.py` — `_provider_mode` already maps string → `FakeProviderMode(name)`; `test_scope_guard.py` allowlist unchanged (docs paths already sanctioned).

## Metrics expectation note

Scenario uses `llm_failure_by_fault_flag: {}` (not `agentic_evidence_gathering_failed: 1`) because `_finish_system_fault` only calls `record_llm_failure` when `is_llm_failure_fault_flag()` is true, and the new flag is intentionally **not** in `LLM_FAILURE_FAULT_FLAGS` — it is a data-layer gathering failure, not an LLM/provider failure metric (same pattern as `config_over_budget` / `correlation_failure`).

## Verification commands

```text
PYTHONPATH=.../src pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py tests/evals/test_eval_harness.py tests/contracts/test_edict_session_trace_hash.py tests/engine/test_engine_ids.py::test_build_decision_edict_copies_session_trace_hash_from_judgment -q
→ 49 passed in 10.93s

ruff check src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine src/praetor/judgment/fake_provider.py evals tests/engine/test_agentic_evidence_gathering_failed_intake.py
→ All checks passed!

mypy src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine/orchestrator.py src/praetor/judgment/fake_provider.py
→ Success: no issues found in 21 source files
```

## TDD evidence

1. Wrote failing intake + edict tests first; intake failed with uncaught `AgenticEvidenceGatheringFailedError`, edict failed with missing `session_trace_hash` attribute.
2. Implemented production wiring; all targeted tests green.
3. `test_outcome_matrix_completeness_guard` passes with new scenario (33 scenarios total).

## Gaps / out of scope

- No commit (per standing order).
- PolicyGate evaluation logic untouched.
- `agentic_evidence_gathering_failed` not added to `LLM_FAILURE_FAULT_FLAGS` (by design).

## Remediation — schema export (session_trace_hash)

Regenerated committed JSON schemas so `session_trace_hash` on `ModelJudgment` (Task 13) and `DecisionEdict` (Task 14) is reflected in contract artifacts.

### Schema files changed

| File | Change |
|---|---|
| `schemas/model_judgment.json` | Added optional `session_trace_hash` (`string \| null`, default `null`) |
| `schemas/decision_edict.json` | Added optional top-level `session_trace_hash` and nested `$defs.ModelJudgment.session_trace_hash` |

No other schema files had content drift (all 14 re-exported; only the two above differ from pre-remediation HEAD).

### Verification commands

```text
PYTHONPATH=.../src python tools/schema_export.py --write
→ Wrote 14 schemas (exit 0)

PYTHONPATH=.../src python tools/schema_export.py --check
→ exit 0 (no drift)

PYTHONPATH=.../src pytest tests/contracts/test_schema_export.py tests/contracts/test_scope_guard.py -q -k schema
→ 10 passed, 5 deselected in 0.85s
```

### Notes

- `tools/schema_export.py` unchanged.
- `schemas/policy_gate_result.json` untouched (PolicyGate not in scope).
- No commit (per standing order).
