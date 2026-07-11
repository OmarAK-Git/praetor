# Verifier Packet — V2-037 Gate 5 Intake Wiring

**verification_model:** claude-opus-4-8-thinking-high
**readonly:** true

## Original goal

V2-037 — Gate 5 intake wiring: persist policy_gate_evaluations from production intake (schema init + record with target_type/asset_class) and inject similar-case exemplars into the judgment prompt on the live orchestrator path.

## Acceptance criteria (only these)

1. Production schema ensure creates `policy_gate_evaluations`; `open_production_state_store` path has the table.
2. Completed `process_alert_intake` persists a `policy_gate_evaluations` row with `target_type` and `asset_class` (first matching asset group, else `ungrouped`; `unknown` when no resolved target).
3. `process_alert_intake` builds the judgment prompt with retrieved human-confirmed similar-case exemplars when precedents exist; empty retrieval leaves prompt without exemplar block.
4. Task-scoped tests cover recording + exemplar injection; disposition/containment behavior unchanged.

## Changed files (implementer claim — verify against disk/diff)

- `src/praetor/policy/containment_policy.py`
- `src/praetor/policy/state.py`
- `src/praetor/engine/orchestrator.py`
- `tests/engine/test_gate5_intake_wiring.py`
- `tests/runtime/test_production_state_init.py`
- `docs/architecture.md`
- `docs/proposals/v2_hardening.md`
- `docs/operator_runbook.md`

## Implementer result (unevidenced until checked)

`.workflow/v2-037-gate5-intake-wiring/results/implementer-result.md`

## Verification commands (run fresh)

```bash
pytest tests/engine/test_gate5_intake_wiring.py tests/runtime/test_production_state_init.py tests/metrics/test_progressive_authorization_reporting.py tests/judgment/test_similar_case_retrieval.py -q
```

## Instructions

- Treat implementer claims as unevidenced until you re-run commands and inspect code.
- Ignore phase-level or sprint-level gaps (`verification.scope` is `task`).
- Confirm recording happens inside the edict critical_transaction and schema init is outside it.
- Confirm asset_class convention: first group / ungrouped / unknown.
- Confirm similar-case path uses retrieve + exemplar_block on excerpt-set builder.
- Write `.workflow/v2-037-gate5-intake-wiring/results/verifier-result.md` with pass/fail, evidence, and any gaps.
- Do not mark the queue item done (controller will).
