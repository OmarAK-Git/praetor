# Plan — V2-037 Gate 5 Intake Wiring

**Tier:** T2  
**Goal (verbatim):** V2-037 — Gate 5 intake wiring: persist policy_gate_evaluations from production intake (schema init + record with target_type/asset_class) and inject similar-case exemplars into the judgment prompt on the live orchestrator path.

**Scope:** Wire existing V2-032/V2-034 libraries into `process_alert_intake` and production schema ensure. No new product features. No phase gate.

## Acceptance criteria

1. Production schema ensure creates `policy_gate_evaluations`; `open_production_state_store` path has the table.
2. Completed `process_alert_intake` persists a `policy_gate_evaluations` row with `target_type` and `asset_class` (first matching asset group, else `ungrouped`; `unknown` when no resolved target).
3. `process_alert_intake` builds the judgment prompt with retrieved human-confirmed similar-case exemplars when precedents exist; empty retrieval leaves prompt without exemplar block.
4. Task-scoped tests cover recording + exemplar injection; disposition/containment behavior unchanged.

## Allowed files

See queue item `files_allowed`.

## Verification

```bash
pytest tests/engine/test_gate5_intake_wiring.py tests/runtime/test_production_state_init.py tests/metrics/test_progressive_authorization_reporting.py tests/judgment/test_similar_case_retrieval.py -q
```

## Design (owner-approved)

- Schema init via `ensure_production_policy_tables` (+ required-table assert).
- Record inside the edict `critical_transaction` after gate evaluation completes to ledger.
- `asset_class`: first matching asset group, else `ungrouped`; `unknown` if no resolved target.
- Similar cases: retrieve before provider call; pass `exemplar_block` into existing excerpt-set prompt builder.
