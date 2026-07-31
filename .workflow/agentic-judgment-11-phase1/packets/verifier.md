# Verifier packet — agentic-judgment-11-phase1

## Goal
Implement Phase 1 source fan-out orchestration with per-source budgets.

## Acceptance criteria
1. Phase 1 fans out four source investigators concurrently with per-source `BudgetTracker` limits.
2. Per-source failures degrade gracefully into the `SessionEvidenceRegistry`.
3. Focused phase tests for Phase 1 pass.

## Changed files
- `src/praetor/judgment/agentic/phases.py` (new)
- `tests/judgment/agentic/test_phases.py` (new)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_phases.py -v`
- `ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py`
- `mypy src/praetor/judgment/agentic/phases.py`

## Focus checks (skeptic)

### 1. Concurrency
Confirm `run_source_fanout` uses `ThreadPoolExecutor(max_workers=4)` and submits all four `run_*_source` helpers.
Confirm registry writes occur only after all futures `.result()` — no concurrent `SessionEvidenceRegistry` mutation from worker threads.

### 2. Per-source budgets
Confirm each `_drive_investigation` creates its own `BudgetTracker(budget=budget)` (counters not shared across sources).
Confirm `test_fanout_respects_budget_and_stops_calling` limits ledger to one tool call when `max_tool_calls=1`.

### 3. Graceful degradation
Confirm per-source success is `any(record.succeeded for record in records)` and failed invocations still produce records appended to registry.
Confirm `SourceFanoutResult.all_failed` is false when any source succeeded (`test_fanout_partial_failure_does_not_mark_all_failed`).
Confirm all-failed path: `test_fanout_all_sources_failed_marks_all_failed`.

### 4. Fixed registry order
Confirm append order is ledger → org-config → similar-cases → wider-telemetry (`record_evidence` / `record_org_config` / `record_exemplars` / `record_evidence`) regardless of thread completion order.

### 5. `wider_telemetry` happy-path deviation (explicit)
Plan Step 1 used `wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=())` with `assert result.wider_telemetry_succeeded is True`.
Implementer changed to `call_plan=({},)`.

Verify independently:
- With `call_plan=()`, `FakeSourceInvestigatorModel` returns `InvestigationSummary` immediately → zero tool calls → `any([])` is `False` for source success.
- Task 13 plan note requires zero-call sources to count as **not succeeded** for `all_failed` (org-config/similar-case use `call_plan=()` in all-fail scenario).
- Implementer change is a test-fixture fix for an inconsistent plan assertion, **not** a production semantic change.

### 6. Boundary / untouched paths
- No changes under `src/praetor/policy/`.
- No changes to single-shot `VertexProvider` / `FakeProvider`.
- Production changes confined to `files_allowed`.

## Implementer result
`.workflow/agentic-judgment-11-phase1/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-11-phase1/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
