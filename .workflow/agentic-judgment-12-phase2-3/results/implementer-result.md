# Implementer result — agentic-judgment-12-phase2-3

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/phases.py` | Added `run_hypothesis_debate` (concurrent malicious/benign case builders over registry facts, zero tool-call budget) and `run_lead_reconciliation` (protected independent budget → `ModelJudgment`). |
| `tests/judgment/agentic/test_phases.py` | Added two focused Phase 2/3 unit tests per plan TDD steps; extended imports for new symbols. |

## Verification commands and outcomes

```text
$ PYTHONPATH=.../src pytest tests/judgment/agentic/test_phases.py -v
6 passed in 0.28s

$ ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py
All checks passed!

$ mypy src/praetor/judgment/agentic/phases.py
Success: no issues found in 1 source file
```

TDD step 2 confirmed expected failure before implementation:

```text
ImportError: cannot import name 'run_hypothesis_debate' from 'praetor.judgment.agentic.phases'
```

## API surface for Task 13

### New public functions

- `run_hypothesis_debate(*, malicious_model: HypothesisModel, benign_model: HypothesisModel, registry: SessionEvidenceRegistry) -> tuple[HypothesisCase, HypothesisCase]`
  - Runs both debaters concurrently via `ThreadPoolExecutor(max_workers=2)`.
  - Reads `registry.facts` only; no tools invoked.
  - Uses internal `PhaseBudget(max_tool_calls=0, max_seconds=15.0)` passed to each model's `build_case`.

- `run_lead_reconciliation(*, lead_model: LeadModel, registry: SessionEvidenceRegistry, malicious_case: HypothesisCase, benign_case: HypothesisCase, budget: PhaseBudget) -> ModelJudgment`
  - Caller supplies an independent Phase 3 budget (not derived from Phase 1/2 leftovers).
  - Delegates to `lead_model.reconcile(registry_facts=registry.facts, malicious_case=..., benign_case=..., budget=...)`.

### Existing Phase 1 surface (unchanged, consumed by Task 13)

- `SourceFanoutResult` — `ledger_history_succeeded`, `org_config_succeeded`, `similar_cases_succeeded`, `wider_telemetry_succeeded`; property `all_failed`.
- `run_source_fanout(*, ledger_model, ledger_tool, org_config_model, org_config_tool, similar_case_model, similar_case_tool, wider_telemetry_model, wider_telemetry_tool, budget, registry) -> SourceFanoutResult`

### Types consumed from sibling modules

- `HypothesisCase`, `HypothesisModel`, `LeadModel` — `praetor.judgment.agentic.model`
- `SessionEvidenceRegistry`, `ToolCallRecord`, etc. — `praetor.judgment.agentic.registry`
- `PhaseBudget` — `praetor.judgment.agentic.budget`
- `ModelJudgment` — `praetor.contracts.judgment`

## Gaps / deviations from plan

1. **Import ordering** — Moved `ModelJudgment` import to precede `praetor.judgment.*` imports for ruff I001 (behavior unchanged).

## Unresolved

None. No commit made per standing orders.
