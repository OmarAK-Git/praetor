# Verifier result — agentic-judgment-03-budget-errors

**Verdict:** `survives`

**Evidence path:** `.workflow/agentic-judgment-03-budget-errors/results/verifier-result.md`

**Worktree:** `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
**PYTHONPATH:** `C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`  
**Verified at:** 2026-07-30 (fresh re-run; implementer transcript treated as unevidenced)

---

## Claim under test

Task `agentic-judgment-03-budget-errors` is done: `PhaseBudget` / `BudgetTracker` / `BudgetExceededError` and `AgenticEvidenceGatheringFailedError` meet the three acceptance criteria.

---

## Fresh commands (re-run)

```text
pytest tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py -v
→ 5 passed in 0.28s

ruff check src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py tests/judgment/agentic/test_budget.py tests/judgment/agentic/test_errors.py
→ All checks passed!

mypy src/praetor/judgment/agentic/budget.py src/praetor/judgment/agentic/errors.py
→ Success: no issues found in 2 source files

git diff HEAD -- src/praetor/policy/
→ 0 content lines (CRLF warnings only; status shows M from line endings, no logic edits)
```

---

## Acceptance criteria

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| `BudgetTracker` permits up to `max_tool_calls` and raises `BudgetExceededError` beyond that, including zero-call budgets | Met | `budget.py:37-41` (`calls_made >= max_tool_calls` before increment); tests `test_budget_tracker_allows_calls_up_to_max`, `test_budget_tracker_raises_when_exceeded`, `test_zero_call_budget_never_permits_a_call` pass; probe: max=2 allows 2 then raises with `calls_made==2`; max=0 raises on first call |
| `PhaseBudget` rejects invalid `max_tool_calls` / `max_seconds` | Met | `budget.py:21-27` (`< 0` / `<= 0`); `test_phase_budget_rejects_invalid_values` covers `-1` and `0.0`; probe: negative `max_seconds` also raises `ValueError` |
| `AgenticEvidenceGatheringFailedError` is a `ProviderError` subclass | Met | `errors.py:8` inherits `praetor.judgment.provider.ProviderError`; `issubclass` test passes; probe: `isinstance(AgenticEvidenceGatheringFailedError('x'), ProviderError)` is True |

---

## Adversarial probes (beyond packet tests)

```text
import from worktree path confirmed (budget_mod ends in .../agentic-judgment/src/.../budget.py)
zero-call budget → BudgetExceededError on first consume_call
max_tool_calls=2 → exactly 2 succeeds, 3rd raises, calls_made==2
PhaseBudget(1, -0.1) → ValueError (max_seconds must be positive)
AgenticEvidenceGatheringFailedError instance is ProviderError
```

All probes passed. Off-by-one semantics match intent (N calls allowed, N+1 raises).

---

## Gaps (non-refuting)

1. **`test_phase_budget_rejects_invalid_values`** covers `max_seconds=0.0` only, not negative — validation path exercised by independent probe.
2. **`test_errors.py`** asserts `issubclass` only — no raise/instantiate smoke in the suite; probe confirmed instance is a `ProviderError`.
3. **`max_seconds`** validated but not enforced by `BudgetTracker` — intentional per plan/docstring; orchestration out of scope.
4. **TDD pre-implementation `ModuleNotFoundError`** not independently reproducible after implementation — final behavior verified; pre-state claim ignored as unevidenced.
5. **`src/praetor/policy/`** shows dirty status from line endings only; no content diff vs HEAD.

---

## Strongest reason

Fresh pytest (5/5), ruff, and mypy are green on the scoped paths; independent runtime probes confirm zero-budget denial, exact N-call allowance with `BudgetExceededError` on N+1, invalid budget rejection, and real `ProviderError` inheritance from the worktree modules — no AC-level falsification found.
