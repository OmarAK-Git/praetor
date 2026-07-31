# Code review — agentic-judgment-11-phase1

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 11 — Phase 1 source fan-out orchestration  
**Spec:** `.workflow/agentic-judgment-11-phase1/plan.md`  
**Design:** `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` (Phase 1 fan-out, per-source budgets, graceful degradation)  
**Plan source:** `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 11

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | `src/praetor/judgment/agentic/phases.py` (new) |
| Tests | `tests/judgment/agentic/test_phases.py` (new) |
| Diff baseline | Matches Task 11 Step 3 in plan doc; minor typing/mypy and test-fixture deltas |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_phases.py -v` → **4 passed** in 0.27s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| PolicyGate / provider | No changes outside `files_allowed` |

---

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| Phase 1 fans out four source investigators concurrently with per-source `BudgetTracker` limits | Met — `ThreadPoolExecutor(max_workers=4)` submits all four `run_*_source` helpers; each `_drive_investigation` constructs its own `BudgetTracker(budget=budget)` |
| Per-source failures degrade gracefully into `SessionEvidenceRegistry` | Met — failed tool results become `succeeded=False` records and are still appended; partial-failure test asserts `all_failed is False` when ledger succeeds |
| Focused Phase 1 tests pass | Met — 4/4 pass (fresh run) |

**Allowed files only:** `phases.py`, `test_phases.py`, workflow artifacts. No policy/provider edits.

**Expected adaptations (not defects):**

- `_StubTool.name = "stub"` — required because `ToolCallRecord.tool_name=tool.name`; plan stub omitted this.
- `TypeVar("_T")` on `_drive_investigation` — mypy-only; behavior matches plan.

---

## Focus-area review

### 1. Concurrency — PASS

`run_source_fanout` (`phases.py:189-219`) submits four workers and blocks on `.result()` in fixed source order. Registry mutation happens only after all futures complete (`phases.py:221-228`), on the calling thread — no concurrent `SessionEvidenceRegistry` writes.

**Gap (non-blocking):** No test proves overlap (timing/barrier). Plan prescribes `ThreadPoolExecutor` only; sequential execution would also pass tests. Acceptable for Task 11 scope.

### 2. Per-source budgets — PASS

Each source path calls `_drive_investigation`, which instantiates a fresh `BudgetTracker` (`phases.py:49`). The shared `PhaseBudget` argument is immutable; counters are not shared across threads.

`test_fanout_respects_budget_and_stops_calling` confirms one over-budget ledger model stops after `max_tool_calls=1` while idle sources use `call_plan=()` (zero calls). Does not prove four independent budgets in one fan-out, but implementation structure is correct per design (“own budget” per subagent).

### 3. Graceful degradation — PASS

- Source success is `any(record.succeeded for record in records)` (`phases.py:91`, `130`, `152`) — one good call salvages the source.
- `SourceFanoutResult.all_failed` (`phases.py:162-169`) is the negated OR of per-source flags — matches Task 11/13 contract.
- `test_fanout_all_sources_failed_marks_all_failed` and `test_fanout_partial_failure_does_not_mark_all_failed` cover aggregate semantics.

Failed records are appended (loops do not filter on `succeeded`). Partial-failure test does not assert registry contents for failed org-config rows — minor coverage gap, not a production defect.

### 4. Fixed registry order — PASS

Docstring and implementation append in ledger → org-config → similar-cases → wider-telemetry order (`phases.py:221-228`), independent of which thread finishes first (results are joined in that order before append).

**Gap (non-blocking):** No test shuffles completion order to pin `session_trace_hash` stability. Task 11 acceptance criteria do not require it; Task 13 provider tests will exercise the hash path.

---

## Deviation analysis: `wider_telemetry` `call_plan=({},)` vs `call_plan=()`

**Verdict: acceptable test fixture adjustment — not a correctness bug.**

| Scenario | `call_plan` | Tool calls | `any(succeeded)` | Consistent with assertions? |
|---|---|---|---|---|
| Plan happy-path (as written) | `()` | 0 | `False` | **No** — contradicts `wider_telemetry_succeeded is True` |
| Implementer happy-path | `({},)` | 1 (stub returns `succeeded=True`) | `True` | **Yes** |
| Task 13 all-sources-fail | ledger/wider: `()` or `({},)` with failing tools; org/similar: `()` | 0 or failed | all `False` | **Yes** — plan note at Task 13 Step 1 explicitly requires “never attempted” ≡ failed for `all_failed` |

Implementation semantics: zero tool calls ⇒ empty `records` ⇒ `any([])` is `False` (`phases.py:91`). That is **intentional** for Task 13 (`docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 13 note, line ~2496): org-config and similar-case with `call_plan=()` contribute no successful source without calling tools.

The plan’s happy-path snippet (`wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=())` at line 1892) is internally inconsistent with `assert result.wider_telemetry_succeeded is True`. The implementer fixed the fixture, not production semantics. Task 13’s own `_make_provider` already uses `call_plan=({},)` for ledger/wider on the success path while leaving org/similar at `()` — confirming zero-call sources are **not** treated as succeeded.

**Conclusion:** Changing wider_telemetry to `call_plan=({},)` preserves `SourceFanoutResult.all_failed` / Task 13 semantics and makes the happy-path test coherent. It does **not** mask a production bug.

---

## Correctness

- `_drive_investigation` stops on `InvestigationSummary`, `BudgetExceededError`, or loop exit — matches plan.
- Unhandled exceptions from `tool.invoke` would propagate through `future.result()`; design’s “graceful degradation” is tool-level `succeeded=False`, not exception swallowing — consistent with plan Step 3.
- `wider_telemetry` records use `registry.record_evidence` (same as ledger) — matches plan.

No logic regressions found vs Task 11 Step 3 reference implementation.

## Security

Read-only orchestration over injected models/tools. No secrets, injection surfaces, or permission widening.

## Simplicity

Thin wrapper over plan reference code. No speculative abstractions. `_StubTool.name` is the minimum fix for `tool.name`.

## Tests

Four tests map 1:1 to plan Step 1. They would fail without `run_source_fanout` / per-source runners (module import + behavior). Budget test pins call count on ledger stub.

**Minor gaps (non-blocking):** no concurrency proof, no registry-order/hash test, partial-failure test omits registry assertions.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_phases.py`** — No test that registry append order is independent of thread completion order; defer to Task 13 `session_trace_hash` coverage or add later.
2. **`tests/judgment/agentic/test_phases.py:118-150`** — Partial-failure case does not assert failed org-config/exemplar records landed in registry.
3. **Plan doc Task 11 Step 1** — `wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=())` should be updated to `({},)` (or drop `wider_telemetry_succeeded is True`) to match implementation semantics; out of scope for this task’s `files_allowed`.

---

## Checked (audit trail)

- Full read of `phases.py` and `test_phases.py`
- Task 11 plan Step 1/3 reference vs implementation
- Task 13 `all_failed` / zero-call note in plan doc
- `FakeSourceInvestigatorModel.next_action` empty-plan behavior
- `BudgetTracker` per-call isolation
- Fresh `pytest` / `ruff` / `mypy` on scoped paths
- No edits under `src/praetor/policy/` or judgment provider paths
