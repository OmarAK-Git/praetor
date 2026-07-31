# Code review — agentic-judgment-03-budget-errors

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 3 — `PhaseBudget` / `BudgetTracker` / `BudgetExceededError` and `AgenticEvidenceGatheringFailedError`  
**Spec:** `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 3; design `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md`

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Diff | Four new untracked files: `budget.py`, `errors.py`, `test_budget.py`, `test_errors.py` (no other scoped source changes) |
| Plan conformance | Implementation and tests match plan Task 3 Steps 1–7 verbatim |
| PolicyGate boundary | `git diff HEAD -- src/praetor/policy/` — no content changes |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py -v` → 5 passed |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_budget.py:28-32`** — `test_phase_budget_rejects_invalid_values` covers `max_seconds=0.0` but not a negative `max_seconds`. Validation rejects `<= 0`; acceptance criteria satisfied; extra negative case would be redundant with plan-prescribed test.

2. **`tests/judgment/agentic/test_errors.py:9-10`** — Only `issubclass` is asserted; no instantiation/raise smoke test. Matches plan Task 3 Step 5 exactly; sufficient for this task’s acceptance criteria.

3. **`budget.py:14-16`** — `max_seconds` is validated at construction but not enforced by `BudgetTracker` (advisory only). Documented in class docstring; intentional per plan scope (“orchestration layer only tracks call count”).

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `BudgetTracker` permits up to `max_tool_calls` and raises `BudgetExceededError` beyond that, including zero-call budgets | Met — `consume_call` uses `calls_made >= max_tool_calls`; zero-budget test passes |
| `PhaseBudget` rejects invalid `max_tool_calls` / `max_seconds` | Met — `__post_init__` guards `< 0` and `<= 0`; validation test passes |
| `AgenticEvidenceGatheringFailedError` is a `ProviderError` subclass | Met — inherits from `praetor.judgment.provider.ProviderError`; issubclass test passes |
| TDD per plan | Met — tests match plan Task 3 Steps 1 & 5 verbatim; implementer documented pre-implementation `ModuleNotFoundError` |
| Files allowed only | Met — changes confined to scoped paths; no `src/praetor/policy/` edits |
| PolicyGate evaluation logic untouched | Met — no policy module content changes |
| Scope: budget + error types only; no phase orchestration | Met — no `phases.py` / provider wiring in this task |

---

## Correctness / security / simplicity

- **Budget semantics:** `max_tool_calls=N` allows exactly N calls (`calls_made` reaches N before next `consume_call` raises). Off-by-one logic is correct.
- **Error hierarchy:** `AgenticEvidenceGatheringFailedError(ProviderError)` aligns with future orchestrator `except` mapping (Task 14).
- **Security:** No I/O, deserialization, or injection surface; pure validation/tracking types.
- **Simplicity:** Minimal prescribed implementation; no duplicate budget abstractions elsewhere in `judgment/agentic/`.

---

## Summary

Implementation matches plan Task 3 exactly. Budget tracking and error type are ready for `phases.py` (Task 11) and provider consumption (Task 12). Proceed to skeptic verification.
