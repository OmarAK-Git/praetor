# Implementer Result — V2-037 Gate 5 Intake Wiring

## Files changed

| File | Rationale |
|---|---|
| `src/praetor/policy/containment_policy.py` | Added `policy_gate_evaluation_dimensions` helper (target_type/asset_class mapping). |
| `src/praetor/policy/state.py` | Wired `init_policy_gate_evaluation_schema` into `ensure_production_policy_tables`; added `policy_gate_evaluations` to required tables. |
| `src/praetor/engine/orchestrator.py` | Early `decision_id`; similar-case exemplar injection before provider call; schema init + `record_policy_gate_evaluation` inside edict `critical_transaction`. |
| `tests/engine/test_gate5_intake_wiring.py` | New task tests for evaluation recording and exemplar prompt injection. |
| `tests/runtime/test_production_state_init.py` | Added `policy_gate_evaluations` to `REQUIRED_PRODUCTION_TABLES`. |
| `docs/architecture.md` | Cleared intake-wiring follow-up note. |
| `docs/proposals/v2_hardening.md` | Cleared Items 3/4 intake follow-up notes. |
| `docs/operator_runbook.md` | Noted automatic evaluation persistence during intake. |

## Design summary

1. **Schema init** — `ensure_production_policy_tables` now calls `init_policy_gate_evaluation_schema`; `policy_gate_evaluations` is in `REQUIRED_PRODUCTION_POLICY_TABLES`. Intake also calls schema init idempotently before the edict `critical_transaction` (outside the transaction per AG-0049).

2. **Evaluation recording** — Inside the edict `critical_transaction`, after ledger append + attempt finalize, `record_policy_gate_evaluation` persists post-stamp `proposed`/`final` from the committed edict. Dimensions: `policy_gate_evaluation_dimensions(snapshot, gate_evaluation.resolved_target)` → first matching asset group else `ungrouped`; `unknown`/`unknown` when `resolved_target` is `None` (e.g. never-contain escalate paths).

3. **Similar-case injection** — Before provider call, `retrieve_similar_case_exemplars` runs with early `decision_id_for_attempt` exclusion; `build_prompt_exemplar_block` feeds `build_judgment_prompt_payload_from_excerpt_set`. Empty retrieval omits `prompt_exemplar_block`.

## Verification command output (verbatim)

```
.................                                                        [100%]
17 passed in 1.69s
```

Command:

```bash
pytest tests/engine/test_gate5_intake_wiring.py tests/runtime/test_production_state_init.py tests/metrics/test_progressive_authorization_reporting.py tests/judgment/test_similar_case_retrieval.py -q
```

## Approval gates / deferred items

None. Queue item not marked done per packet instructions.
