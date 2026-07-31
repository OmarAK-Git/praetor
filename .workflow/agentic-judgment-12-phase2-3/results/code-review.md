# Code review — agentic-judgment-12-phase2-3

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 12 — Phase 2 hypothesis debate and Phase 3 lead reconciliation  
**Spec:** `.workflow/agentic-judgment-12-phase2-3/plan.md`  
**Design:** `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` (Phase 2 reasoning-only, Phase 3 protected budget)

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | `src/praetor/judgment/agentic/phases.py` (untracked) — appended `run_hypothesis_debate`, `run_lead_reconciliation` after Phase 1 fan-out |
| Tests | `tests/judgment/agentic/test_phases.py` (untracked) — 4 Phase 1 + 2 Phase 2/3 tests |
| Plan alignment | Phase 2/3 implementation matches Task 12 Step 3 in `docs/superpowers/plans/2026-07-30-agentic-judgment.md` |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_phases.py -v` → **6 passed** in 0.28s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| PolicyGate boundary | Task changes confined to `phases.py` / `test_phases.py`; no edits inside `src/praetor/policy/` from this task |

---

## Focus-area review

### 1. Phase 2 — malicious/benign debate over registry, no tools — PASS

`phases.py:245-269` — `run_hypothesis_debate` reads `registry.facts` only; no tool parameters or invocations in the orchestration surface. Both debaters run concurrently via `ThreadPoolExecutor(max_workers=2)` with stances `"malicious"` and `"benign"`. Internal `PhaseBudget(max_tool_calls=0, max_seconds=15.0)` is passed to each `build_case` call, matching spec's reasoning-only Phase 2.

`test_phases.py:192-226` — `test_hypothesis_debate_runs_both_stances` seeds registry with one fact, asserts malicious case reflects `1-facts` key point and both stances are returned.

### 2. Phase 3 — independently protected budget → ModelJudgment — PASS

`phases.py:272-289` — `run_lead_reconciliation` accepts caller-supplied `budget` (not derived from Phase 1/2 leftovers) and returns `ModelJudgment` via `lead_model.reconcile(...)`, passing `registry_facts`, both hypothesis cases, and budget. Docstring documents the protected-allotment contract for Task 13 composition.

`test_phases.py:229-249` — `test_lead_reconciliation_produces_judgment` supplies an independent `PhaseBudget(max_tool_calls=0, max_seconds=15.0)` and asserts `Disposition.ESCALATE` on the returned judgment.

### 3. Phase 1 untouched — PASS (minor drift noted)

Phase 1 fan-out (`_drive_investigation` through `run_source_fanout`, lines 45-242) matches Task 11 plan logic. Task 12 additions are append-only after line 244. Non-functional Phase 1 drift vs Task 11 plan prescription:

- `TypeVar("_T")` generic on `_drive_investigation` invoke callback (plan used `object`) — type-safety refinement, behavior unchanged.
- Import reorder: `ModelJudgment` import grouped with contracts import block for ruff I001.

Four existing Phase 1 tests still pass unchanged — no regression signal.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`test_phases.py:192-226`** — Phase 2 test does not assert `benign_case.key_points == ("benign-explanation",)`; only malicious key points are checked. Plan-prescribed test matches this; low risk.

2. **`phases.py:245-269`** — No orchestration-layer guard that `build_case` never invokes tools; enforcement relies on `max_tool_calls=0` budget passed to model backends and absence of tools in the function signature. Matches plan and spec's "reasoning-only" framing; structural no-tool test deferred to real model / provider integration (Task 13).

3. **`phases.py:272-289`** — Protected budget is contractual (caller responsibility + docstring), not runtime-enforced in `phases.py`. Plan Step 3 uses the same pattern; Task 13 provider must allocate Phase 3 budget independently.

4. **`phases.py` / `test_phases.py`** — Files untracked (`??`); expected per standing order not to commit.

5. **Worktree drift** — `src/praetor/policy/` shows unrelated `M` modifications elsewhere in the worktree; not introduced by this task's allowed files.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| Phase 2 runs malicious and benign hypothesis cases over the registry without tools | Met — concurrent `build_case` over `registry.facts`; `max_tool_calls=0`; no tool surface |
| Phase 3 has independently protected budget and produces ModelJudgment for provider | Met — caller-supplied `budget`; returns `ModelJudgment` from `LeadModel.reconcile` |
| Focused phase tests cover Phase 2/3 | Met — two new tests per plan TDD steps |
| Phase 1 untouched | Met — append-only; Phase 1 tests pass; only minor typing/import drift |
| Files allowed only | Met — production/test changes in scoped paths |
| PolicyGate evaluation logic untouched | Met — no policy changes from this task |

---

## Correctness / security / simplicity

- **Concurrency:** Phase 2 reads `registry.facts` immutably during debate; no registry mutation — thread-safe for concurrent debaters.
- **Budget sharing:** Single frozen `PhaseBudget` instance passed to both debaters is immutable; orchestration does not share a `BudgetTracker` across threads.
- **Security:** No new injection or deserialization surface; facts flow through existing model Protocol trust boundary.
- **Simplicity:** Implementation matches plan Task 12 Step 3 verbatim; no duplicate orchestration helpers.

---

## Summary

Phase 2 and Phase 3 orchestration match the approved plan and design spec. Phase 1 fan-out is unchanged in behavior with only minor typing/import refinements. All six focused tests pass; lint and mypy clean. Proceed to skeptic verification.
