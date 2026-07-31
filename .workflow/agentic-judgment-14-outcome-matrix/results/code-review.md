# Code Review — agentic-judgment-14-outcome-matrix

**Verdict: PASS**

**Scope:** Outcome Matrix row `agentic_evidence_gathering_failed`, orchestrator catch via `_finish_system_fault`, `DecisionEdict.session_trace_hash` pass-through, harness scenario, DEC-064 docs  
**Plan:** `.workflow/agentic-judgment-14-outcome-matrix/plan.md`  
**Implementer result:** `.workflow/agentic-judgment-14-outcome-matrix/results/implementer-result.md`

## Summary

Task 14 registers the `agentic_evidence_gathering_failed` Outcome Matrix row, routes `AgenticEvidenceGatheringFailedError` through `_finish_system_fault` (not `_finish_provider_fault`), threads optional `session_trace_hash` from `ModelJudgment` onto `DecisionEdict`, adds harness coverage, and documents DEC-064. All seven user critical checks pass. PolicyGate evaluation logic is untouched.

## Critical checks (user-requested)

| # | Check | Result |
|---|---|---|
| 1 | Orchestrator uses `_finish_system_fault` (no provider breaker trip) | **Pass** — `orchestrator.py:412–418` calls `_finish_system_fault` directly; no `in_transaction_hook` / `record_provider_breaker_metrics`. `test_agentic_evidence_gathering_failed_does_not_trip_breaker` confirms `production_failure_total` unchanged. |
| 2 | Completeness guard intact and passes | **Pass** — `test_outcome_matrix_completeness_guard` green; 33 scenarios; `REQUIRED_MATRIX_PAIRS` fully covered including new flag. |
| 3 | PolicyGate evaluation files zero semantic diffs | **Pass** — `git diff --numstat -- src/praetor/policy/` shows no line changes (CRLF warnings only). |
| 4 | FakeProvider/Vertex single-shot path intact except `FakeProviderMode` | **Pass** — `fake_provider.py` adds enum value + raise branch only; existing modes unchanged. `vertex_provider.py` has no diff. Harness `_provider_mode` maps strings dynamically (`harness.py:473–474`). |
| 5 | DEC-064 docs present; `org_config_section` NOT corroboration-eligible | **Pass** — `docs/decisions.md` index + full DEC-064 section; `docs/contracts.md` §13 row + `DOMAIN_SESSION_TRACE` section; `docs/architecture.md` agentic package row. DEC-064 explicitly excludes `org_config_section` and `similar_cases` from corroboration. |
| 6 | `session_trace_hash` threading correct | **Pass** — `DecisionEdict.session_trace_hash: str \| None = None` (`contracts/edict.py:28–31`); `build_decision_edict` copies `judgment.session_trace_hash` (`engine/edict.py:109`); contract + engine tests assert default `None` and round-trip. |
| 7 | Scenario metrics match `_finish_system_fault` behavior | **Pass** — scenario uses `llm_failure_by_fault_flag: {}` (not `agentic_evidence_gathering_failed: 1`). Correct: `_record_intake_metrics_bypass_gate` only calls `record_llm_failure` when `is_llm_failure_fault_flag()` is true (`orchestrator.py:170–171`), and `AGENTIC_EVIDENCE_GATHERING_FAILED` is intentionally absent from `LLM_FAILURE_FAULT_FLAGS` (`events.py:64–71`). Same pattern as `correlation_failure` / `config_over_budget` scenarios. |

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| `AgenticEvidenceGatheringFailedError` → escalate + `agentic_evidence_gathering_failed` + `system_fault_escalation=true` without breaker trip | Met |
| `DecisionEdict.session_trace_hash` optional, copied from `ModelJudgment` | Met |
| Outcome Matrix completeness guard passes with new scenario | Met |
| DEC-064 + contracts/architecture docs updated; PolicyGate evaluation unchanged | Met |
| Committed schemas regenerated for `session_trace_hash`; `schema_export.py --check` passes | Met (remediation) |
| PolicyGate logic untouched | Met |

**Allowed-files deviation (non-blocking):** Plan listed `tests/engine/test_edict_session_trace_hash.py`; engine pass-through test lives in `tests/engine/test_engine_ids.py::test_build_decision_edict_copies_session_trace_hash_from_judgment` instead. Coverage is equivalent.

**Incidental orchestrator change:** `JudgmentRequest(..., evidence_bundle=resolved_bundle)` added (`orchestrator.py:368–371`). Backward compatible (optional field); required for agentic providers; within `orchestrator.py` allowlist.

**Not changed (acceptable):** `evals/harness.py` — dynamic `FakeProviderMode(name)` already supports new mode string.

## Correctness

- `OUTCOME_MATRIX_SFE[AGENTIC_EVIDENCE_GATHERING_FAILED] = True` in `fault_flags.py:24` matches docs §13 SFE polarity.
- Catch ordering: `AgenticEvidenceGatheringFailedError` handler is separate from `_finish_provider_fault` paths; subclasses `ProviderError` but is not an LLM failure metric.
- `_finish_system_fault` builds skeleton judgment with `STANDARD_REVIEW` proposed disposition, escalates with `system_fault=True`, bypasses gate metrics — consistent with `provider_unavailable` SFE semantics minus breaker hook.

## Security

- No injection, secrets, permission widening, or PolicyGate evaluation changes.
- Fault-flag registration follows existing enum + `OUTCOME_MATRIX_SFE` pattern.

## Simplicity

- Minimal diff: one enum value, one SFE entry, one catch block, one FakeProvider mode, one optional edict field, one scenario YAML, docs.
- No duplicate abstractions or speculative generality.

## Tests

Fresh re-run (reviewer, `PYTHONPATH=.../src`):

| Command | Result |
|---|---|
| `pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py tests/evals/test_eval_harness.py tests/contracts/test_edict_session_trace_hash.py tests/engine/test_engine_ids.py::test_build_decision_edict_copies_session_trace_hash_from_judgment -q` | **49 passed** |
| `pytest tests/evals/test_eval_harness.py::test_outcome_matrix_completeness_guard -q` | **1 passed** |
| `pytest tests/evals/test_eval_harness.py::test_harness_all_scenarios_pass -q` | **1 passed** (33 scenarios) |
| `ruff check` (plan paths) | All checks passed |
| `mypy` (plan paths) | Success: 21 files |

## Findings

### Critical

None.

### Important

None (schema drift resolved — see Remediation review below).

### Minor (non-blocking)

| Location | Issue | Suggested fix |
|---|---|---|
| Plan vs implementation | `tests/engine/test_edict_session_trace_hash.py` not created; engine test in `test_engine_ids.py` | Align filename with plan or update plan allowlist |
| `tests/contracts/test_edict_session_trace_hash.py` | Tests `ModelJudgment` only; no `DecisionEdict` contract round-trip | Optional: add `DecisionEdict` serialization test (engine test covers build path) |

## Verdict rationale

All plan acceptance criteria and all seven user critical checks pass. Orchestrator correctly distinguishes data-layer gathering failure from provider-health faults. Harness scenario metrics align with `_finish_system_fault` / non-LLM-failure semantics. PolicyGate evaluation code is unchanged. **PASS** — ready for skeptic-verify.

---

## Remediation review — schema export (`session_trace_hash`)

**Remediation verdict: PASS**

**Scope:** Regenerate committed JSON schemas for Task 13/14 `session_trace_hash` fields; confirm PolicyGate schema untouched; confirm `schema_export.py --check` passes.

### Checks

| # | Check | Result |
|---|---|---|
| 1 | Only `schemas/model_judgment.json` and `schemas/decision_edict.json` gained `session_trace_hash` | **Pass** — `git diff HEAD --ignore-cr-at-eol -- schemas/` shows content changes only in those two files; no other schema file has semantic drift |
| 2 | `model_judgment.json` field shape matches contract | **Pass** — optional `session_trace_hash` (`string \| null`, default `null`) at top level (`schemas/model_judgment.json:96–107`) |
| 3 | `decision_edict.json` field shape matches contract | **Pass** — optional top-level `session_trace_hash` (`schemas/decision_edict.json:355–367`) and nested `$defs.ModelJudgment.session_trace_hash` (`schemas/decision_edict.json:216–227`) |
| 4 | PolicyGate schema untouched | **Pass** — `schemas/policy_gate_result.json` has zero content diff vs HEAD (`--ignore-cr-at-eol`); no `session_trace_hash` in any other schema |
| 5 | `python tools/schema_export.py --check` | **Pass** — exit 0 |
| 6 | Contract tests | **Pass** — `test_committed_schemas_match_export`, `test_schema_export_cli_check_passes`, `test_scope_guard.py` (9 passed) |

### Remediation rationale

Prior Important finding (committed-schema drift blocking `test_scope_guard.py`) is fully resolved. Schema additions are minimal, optional-with-default, and aligned with `ModelJudgment` / `DecisionEdict` Pydantic definitions. No PolicyGate or unrelated schema surface changed. **PASS** — remediation complete; no blockers remain for Task 14.
