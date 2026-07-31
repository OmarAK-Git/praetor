# Verifier packet — agentic-judgment-09-model-protocols

## Goal
Define `SourceInvestigatorModel` / `HypothesisModel` / `LeadModel` Protocols and supporting result dataclasses. Protocol surfaces only — no real LLM wire integration.

## Acceptance criteria
- Protocols exist for source investigator, hypothesis, and lead models as specified in the plan.
- Structural protocol tests pass.

## Changed files
- `src/praetor/judgment/agentic/model.py` — new: frozen dataclasses + three `@runtime_checkable` Protocols
- `tests/judgment/agentic/test_model.py` — new: three structural dataclass tests

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_model.py -v`
- `ruff check src/praetor/judgment/agentic/model.py tests/judgment/agentic/test_model.py`
- `mypy src/praetor/judgment/agentic/model.py`

## Focus checks (skeptic)

### 1. Protocol surfaces (CRITICAL — Task 10/11 consumers)
In `src/praetor/judgment/agentic/model.py`, confirm all three Protocols exist and are `@runtime_checkable`:

| Protocol | Method | Return type |
|----------|--------|-------------|
| `SourceInvestigatorModel` | `next_action(*, prior_call_count: int, last_call_succeeded: bool \| None)` | `ToolCallDecision \| InvestigationSummary` |
| `HypothesisModel` | `build_case(*, stance: str, registry_facts: Sequence[EvidenceFact], budget: PhaseBudget)` | `HypothesisCase` |
| `LeadModel` | `reconcile(*, registry_facts: Sequence[EvidenceFact], malicious_case: HypothesisCase, benign_case: HypothesisCase, budget: PhaseBudget)` | `ModelJudgment` |

Cross-check against `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 9 interfaces block (~1530). No extra methods, no missing keyword-only params.

### 2. Result dataclasses
Confirm frozen dataclasses:

- `ToolCallDecision(arguments: dict[str, Any])` — `model.py:22-26`
- `InvestigationSummary(narrative: str)` — `model.py:29-33`
- `HypothesisCase(stance: str, key_points: tuple[str, ...], cited_evidence_ids: tuple[str, ...], narrative: str)` — `model.py:36-41`

All three must use `@dataclass(frozen=True)`.

### 3. Imports and type dependencies
Confirm imports resolve without circular dependency:

- `EvidenceFact` from `praetor.contracts.evidence`
- `ModelJudgment` from `praetor.contracts.judgment`
- `PhaseBudget` from `praetor.judgment.agentic.budget`

`mypy src/praetor/judgment/agentic/model.py` must succeed.

### 4. Structural tests (Task 9 scope only)
`tests/judgment/agentic/test_model.py` must contain exactly the three plan-prescribed tests:

- `test_tool_call_decision_is_frozen` — constructs `ToolCallDecision`, asserts `arguments`
- `test_investigation_summary_holds_narrative` — asserts `narrative` field
- `test_hypothesis_case_fields` — asserts `stance` and `key_points`

**Do not** require Protocol `isinstance` tests in this task — those belong to Task 10 (`fake_model.py`). Confirm `test_model.py` does **not** import `Fake*` implementations.

### 5. Scope / untouched paths
- No changes under `src/praetor/policy/`.
- No changes to `VertexProvider` / `FakeProvider` single-shot behavior.
- No `fake_model.py` or `phases.py` in this task (Tasks 10–11).
- Production changes confined to `files_allowed`.

### 6. No LLM wire integration
Confirm `model.py` contains no HTTP/client imports, no prompt templates, no Gemini/function-calling code. Module docstring should state real backend is deferred follow-on work.

## Implementer result
`.workflow/agentic-judgment-09-model-protocols/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-09-model-protocols/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
