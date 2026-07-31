# Verifier result — agentic-judgment-12-phase2-3

**Verdict: PASS (survives)**

**Claim under test:** Task 12 is done — Phase 2 runs concurrent malicious/benign hypothesis cases over registry facts with no tools (`max_tool_calls=0`); Phase 3 accepts an independently supplied budget and returns `ModelJudgment`; focused Phase 2/3 tests pass; Phase 1 fan-out behavior untouched; PolicyGate / allowed-file boundaries held.

---

## Fresh command evidence

Working directory: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`

| Command | Outcome |
|---|---|
| `pytest tests/judgment/agentic/test_phases.py -v` | **6 passed** in 0.28s |
| `ruff check src/praetor/judgment/agentic/phases.py tests/judgment/agentic/test_phases.py` | All checks passed |
| `mypy src/praetor/judgment/agentic/phases.py` | Success: no issues found in 1 source file |
| `git diff --numstat HEAD -- src/praetor/policy/` | **0 content lines** (CRLF dirt only; no PolicyGate content change) |
| Independent spy probe (temp script) | `phase2_spy_ok` / `phase3_spy_ok` / `verdict_probe_pass` |

---

## Focus-check findings

### 1. Phase 2 — no tools, both stances — survives

- `run_hypothesis_debate` (`phases.py:245-269`): signature has no tool parameters; reads `facts = registry.facts` only; submits `malicious_model.build_case(stance="malicious", ...)` and `benign_model.build_case(stance="benign", ...)` via `ThreadPoolExecutor(max_workers=2)`.
- Internal budget is `PhaseBudget(max_tool_calls=0, max_seconds=15.0)` (`phases.py:255`).
- Matches plan Task 12 Step 3 verbatim (`docs/superpowers/plans/2026-07-30-agentic-judgment.md:2312-2330`).
- `test_hypothesis_debate_runs_both_stances` (`test_phases.py:192-226`): registry seeded with one fact → `malicious_case.key_points == ("1-facts",)`; both stances asserted.
- Spy probe: both models receive `n=1` facts and `budget.max_tool_calls==0` / `max_seconds==15.0`.

**Gap (non-blocking):** Suite does not assert `benign_case.key_points` or that budget was forwarded (plan-prescribed test omits both). Concurrency is not temporally proven — sequential substitution would still pass. No-tools is structural (no tool surface + zero call budget); `FakeHypothesisModel` discards `budget` (`fake_model.py:48`).

### 2. Phase 3 — protected independent budget → ModelJudgment — survives

- `run_lead_reconciliation` (`phases.py:272-289`): `budget: PhaseBudget` is a required caller argument (not computed from Phase 1/2 leftovers); returns `lead_model.reconcile(..., budget=budget)` → `ModelJudgment`.
- Docstring encodes the protected-allotment contract for Task 13.
- `test_lead_reconciliation_produces_judgment` (`test_phases.py:229-249`): independent `PhaseBudget(max_tool_calls=0, max_seconds=15.0)` → `proposed_disposition == Disposition.ESCALATE`.
- Spy probe: reconcile receives the identical `budget` object (`is` identity), both cases, and `registry_facts` length 1.

**Gap (non-blocking):** Protection is contractual (API + docstring), not runtime-enforced against leftover derivation — Task 13 must allocate independently. Fake lead factory ignores kwargs; suite alone does not prove case/budget wire-through (spy does).

### 3. Phase 1 untouched — survives

- Phase 1 body (`_drive_investigation` through `run_source_fanout`, `phases.py:45-242`) ends before append-only Phase 2/3 (`def run_hypothesis_debate` at line 245).
- Four Phase 1 tests still pass in the same suite run.
- Task 11 already introduced `TypeVar("_T")` typing drift; Task 12 only adds imports + Phase 2/3 functions (plus `ModelJudgment` import ordering for ruff I001).

**Gap (non-blocking):** No byte-identical Phase 1 snapshot to diff against; behavioral regression signal is the four still-green Phase 1 tests + append-only layout.

### 4. Boundaries — survives

- Production/test changes for this task are confined to untracked `phases.py` and `test_phases.py` (plus `.workflow/agentic-judgment-12-phase2-3/`).
- `src/praetor/policy/` shows `M` in `git status` but `git diff` has **zero content lines** (line-ending dirt only) — not introduced as PolicyGate logic changes by this task.

---

## Acceptance criteria map

| Criterion | Verdict |
|---|---|
| Phase 2 malicious+benign over registry without tools | Survives |
| Phase 3 independently protected budget → ModelJudgment | Survives |
| Focused Phase 2/3 tests | Survives (2 tests; 6/6 suite green) |
| Phase 1 fan-out untouched (behavior) | Survives |
| PolicyGate untouched / files allowed | Survives |

---

## Strongest reason this survives

Fresh pytest/ruff/mypy are green; implementation matches the approved plan Step 3 text; independent spies confirm stance/facts/budget forwarding that the weak Fake-based tests omit; Phase 1 remains append-only with all four prior tests still passing; policy content diff is empty.

## Strongest residual risk (does not flip verdict)

Phase 3 “protected budget” and Phase 2 “no tools” are orchestration contracts, not hard runtime guards — a careless Task 13 composer or a tool-capable hypothesis backend that ignores `max_tool_calls=0` could still violate the design intent.
