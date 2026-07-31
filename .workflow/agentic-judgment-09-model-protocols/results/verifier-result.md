# Verifier result — agentic-judgment-09-model-protocols

**Verdict:** PASS (survives)
**Role:** skeptic-verifier (fresh context; independent of implementer reasoning)

## Claim restated

Task 9 is done: `model.py` defines frozen result dataclasses and three `@runtime_checkable` Protocols (`SourceInvestigatorModel` / `HypothesisModel` / `LeadModel`) matching the plan Task 9 interfaces; structural tests pass; no LLM wire integration; production changes confined to `files_allowed`.

## Evidence gathered (independent)

### Commands (fresh, `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)

| Command | Result |
|---------|--------|
| `pytest tests/judgment/agentic/test_model.py -v` | **3 passed** in 0.27s |
| `ruff check src/praetor/judgment/agentic/model.py tests/judgment/agentic/test_model.py` | All checks passed |
| `mypy src/praetor/judgment/agentic/model.py` | Success: no issues found in 1 source file |

### Focus 1 — Protocol surfaces (`model.py:44-74`)

Cross-checked against `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 9 (~1530, Step 3 ~1620–1646) and runtime `inspect.signature`:

| Protocol | `@runtime_checkable` | Method | Keyword-only params | Return |
|----------|----------------------|--------|---------------------|--------|
| `SourceInvestigatorModel` | yes (`_is_runtime_protocol=True`) | `next_action` | `prior_call_count`, `last_call_succeeded` | `ToolCallDecision \| InvestigationSummary` |
| `HypothesisModel` | yes | `build_case` | `stance`, `registry_facts`, `budget` | `HypothesisCase` |
| `LeadModel` | yes | `reconcile` | `registry_facts`, `malicious_case`, `benign_case`, `budget` | `ModelJudgment` |

No extra methods. `HypothesisModel.build_case` signature line-wrap only (ruff E501); semantically identical to plan.

### Focus 2 — Result dataclasses (`model.py:22-41`)

All three use `@dataclass(frozen=True)`. Runtime mutation probe:

- `ToolCallDecision` → `FrozenInstanceError`
- `InvestigationSummary` → `FrozenInstanceError`
- `HypothesisCase` → `FrozenInstanceError`

Fields match plan: `arguments: dict[str, Any]`; `narrative: str`; `stance` / `key_points: tuple[str, ...]` / `cited_evidence_ids: tuple[str, ...]` / `narrative`.

### Focus 3 — Imports / type dependencies

Resolved at import and under mypy:

- `EvidenceFact` ← `praetor.contracts.evidence`
- `ModelJudgment` ← `praetor.contracts.judgment`
- `PhaseBudget` ← `praetor.judgment.agentic.budget`

No circular import failure observed.

### Focus 4 — Structural tests (`test_model.py`)

Exactly the three plan-prescribed tests; no `Fake*` imports; no `isinstance` Protocol checks (correctly deferred to Task 10).

### Focus 5 — Scope

- `fake_model.py` absent; `phases.py` absent.
- Task production artifact: `src/praetor/judgment/agentic/model.py` (new).
- Task test artifact: `tests/judgment/agentic/test_model.py` (new).
- `src/praetor/policy/*` shows dirty status but `git diff --numstat` is empty (CRLF noise only) — not a Task 9 content change.
- No VertexProvider / FakeProvider edits attributed to this task.

### Focus 6 — No LLM wire

`model.py` imports are stdlib typing/dataclasses + local contracts/budget only. No HTTP/client imports. Module docstring states Gemini/function-calling backend is deferred follow-on work (plan-aligned mention only).

## Attack angles that did not refute

| Attack | Outcome |
|--------|---------|
| Protocols missing / wrong arity / positional params | Refuted — signatures keyword-only and complete |
| `@dataclass(frozen=True)` claimed but not enforced | Refuted — `FrozenInstanceError` on setattr |
| Tests pass without module / wrong module | Refuted — import path is `praetor.judgment.agentic.model`; 3/3 pass |
| Scope creep into Task 10/11 or policy | Refuted for this task’s deliverables |
| LLM wire sneaked in | Refuted |

## Gaps (non-blocking; plan-prescribed)

1. **`test_tool_call_decision_is_frozen`** asserts field equality only — does not assert `FrozenInstanceError`. Name overclaims; matches plan Step 1 verbatim. Frozenness confirmed independently above.
2. **`test_hypothesis_case_fields`** asserts `stance` / `key_points` only — does not assert `cited_evidence_ids` / `narrative` (constructed but unchecked). Matches plan Step 1.
3. **`ToolCallDecision.arguments`** is a mutable `dict` inside a frozen dataclass; retaining a reference allows content mutation (`dict_mut_via_ref` probe → `{'a': 99}`). Plan-prescribed; Task 10 fakes copy via `dict(...)`.
4. **No Protocol `isinstance` tests** in this task — intentional per packet/plan (Task 10).

## Strongest reason the claim survives

Fresh pytest/ruff/mypy all pass, and the Protocol/dataclass surfaces in `model.py` match the Task 9 plan interfaces (including `@runtime_checkable` and keyword-only params) with no out-of-scope LLM or Task 10/11 artifacts. Remaining gaps are weaknesses of the plan’s own prescribed tests, not unmet acceptance criteria.
