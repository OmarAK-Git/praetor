# Verifier packet — agentic-judgment-12-phase2-3

## Goal
Implement Phase 2 hypothesis debate and Phase 3 lead reconciliation with protected budgets.

## Acceptance criteria
- Phase 2 runs malicious and benign hypothesis cases over the registry without tools.
- Phase 3 has an independently protected budget and produces the final ModelJudgment surface needed by the provider.
- Focused phase tests cover Phase 2/3.
- Phase 1 fan-out untouched (behavior).

## Changed files
- `src/praetor/judgment/agentic/phases.py` (untracked)
- `tests/judgment/agentic/test_phases.py` (untracked)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_phases.py -v`
- `ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py`
- `mypy src/praetor/judgment/agentic/phases.py`

## Focus checks (skeptic)

### Phase 2 — no tools, both stances
1. **`run_hypothesis_debate`** (`phases.py:245-269`): confirm no tool parameters; reads `registry.facts` only; runs `malicious_model.build_case(stance="malicious", ...)` and `benign_model.build_case(stance="benign", ...)` concurrently.
2. Confirm internal budget is `PhaseBudget(max_tool_calls=0, max_seconds=15.0)`.
3. **`test_hypothesis_debate_runs_both_stances`**: registry seeded with one fact → malicious `key_points == ("1-facts",)`; both stances returned.

### Phase 3 — protected independent budget → ModelJudgment
4. **`run_lead_reconciliation`** (`phases.py:272-289`): `budget` is a caller argument (not computed from Phase 1/2); returns `ModelJudgment` from `lead_model.reconcile(registry_facts=..., malicious_case=..., benign_case=..., budget=...)`.
5. **`test_lead_reconciliation_produces_judgment`**: independent `PhaseBudget(max_tool_calls=0, max_seconds=15.0)` → `judgment.proposed_disposition == Disposition.ESCALATE`.

### Phase 1 untouched
6. Phase 1 functions (`_drive_investigation` through `run_source_fanout`, lines 45-242) present and unchanged in behavior; four Phase 1 tests still pass:
   - `test_fanout_runs_all_four_sources_and_records_registry`
   - `test_fanout_all_sources_failed_marks_all_failed`
   - `test_fanout_partial_failure_does_not_mark_all_failed`
   - `test_fanout_respects_budget_and_stops_calling`

### Boundaries
7. **PolicyGate untouched:** no content changes to `src/praetor/policy/` from this task.
8. **Files allowed only:** changes confined to `phases.py`, `test_phases.py`, and `.workflow/agentic-judgment-12-phase2-3/`.

## Implementer result
`.workflow/agentic-judgment-12-phase2-3/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-12-phase2-3/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
