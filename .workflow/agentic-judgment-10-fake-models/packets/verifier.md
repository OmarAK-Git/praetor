# Verifier packet — agentic-judgment-10-fake-models

## Goal
Add deterministic `FakeSourceInvestigatorModel`, `FakeHypothesisModel`, and `FakeLeadModel` implementing the Task 9 model Protocols. Fake model implementations only — no provider composition.

## Acceptance criteria
- `FakeSourceInvestigatorModel` / `FakeHypothesisModel` / `FakeLeadModel` implement the Protocols deterministically.
- Fakes never read `EvidenceFact.raw_source`.
- Focused fake-model tests pass.

## Changed files
- `src/praetor/judgment/agentic/fake_model.py` — new: three `@dataclass` Fake* implementations
- `tests/judgment/agentic/test_fake_model.py` — new: three behavioral unit tests

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_fake_model.py -v`
- `ruff check src/praetor/judgment/agentic/fake_model.py tests/judgment/agentic/test_fake_model.py`
- `mypy src/praetor/judgment/agentic/fake_model.py`

## Focus checks (skeptic)

### 1. Fake implementations (CRITICAL — Task 11/12 consumers)

In `src/praetor/judgment/agentic/fake_model.py`, confirm all three classes exist and match Task 10 Step 3:

| Class | Key behavior |
|-------|--------------|
| `FakeSourceInvestigatorModel` | `call_plan: tuple[dict[str, object], ...]`; `next_action` replays plan entries by `prior_call_count` via `ToolCallDecision(arguments=dict(...))`; when exhausted returns `InvestigationSummary(narrative=summary_narrative)` |
| `FakeHypothesisModel` | `case_factory: Callable[[str, Sequence[EvidenceFact]], HypothesisCase]`; `build_case` delegates to factory with `stance` and `registry_facts` |
| `FakeLeadModel` | `judgment_factory: Callable[..., ModelJudgment]`; `reconcile` delegates with `registry_facts`, `malicious_case`, `benign_case` keyword args |

Cross-check against `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 10 (~1746–1807). No extra public methods.

### 2. Protocol conformance (CRITICAL)

Using Task 9 `@runtime_checkable` Protocols from `praetor.judgment.agentic.model`:

```python
from praetor.judgment.agentic.fake_model import (
    FakeSourceInvestigatorModel, FakeHypothesisModel, FakeLeadModel,
)
from praetor.judgment.agentic.model import (
    SourceInvestigatorModel, HypothesisModel, LeadModel,
)
assert isinstance(FakeSourceInvestigatorModel(), SourceInvestigatorModel)
assert isinstance(FakeHypothesisModel(case_factory=lambda s, f: ...), HypothesisModel)
assert isinstance(FakeLeadModel(judgment_factory=lambda **k: ...), LeadModel)
```

All three must be `True`. Method signatures must be keyword-only where the Protocol specifies `*`.

### 3. `raw_source` isolation (CRITICAL — DEC-047)

- Grep `fake_model.py` for `raw_source` → **must be zero matches**.
- Confirm fake implementations do **not** access any `EvidenceFact` attributes (no `.field` access on fact instances). Passing `Sequence[EvidenceFact]` through to an injected factory is acceptable; the fake itself must not read fields.
- Optional: grep entire worktree `*.py` for `raw_source` in agentic judgment paths — should find no reads in fake model code.

### 4. Determinism

- `FakeSourceInvestigatorModel.next_action`: replay driven only by `prior_call_count` and `len(call_plan)`; `last_call_succeeded` must not change which plan entry is returned.
- Same inputs to factory fakes must yield same outputs (factories are injected; fakes add no randomness or I/O).

### 5. Behavioral tests

`tests/judgment/agentic/test_fake_model.py` must contain the three plan-prescribed tests:

- `test_fake_source_investigator_replays_call_plan_then_summarizes` — two `ToolCallDecision` then `InvestigationSummary`
- `test_fake_hypothesis_model_delegates_to_factory` — stance and key_points from factory
- `test_fake_lead_model_delegates_to_factory` — `Disposition.ESCALATE` via `skeleton_model_judgment`

All three must pass under pytest.

### 6. Scope / untouched paths
- No changes under `src/praetor/policy/`.
- No changes to `VertexProvider` / `FakeProvider` single-shot behavior.
- No `phases.py` or `AgenticJudgmentProvider` in this task (Tasks 11–12).
- Production changes confined to `files_allowed`.

### 7. No provider composition
Confirm `fake_model.py` contains no HTTP/client imports, no orchestration logic, no Gemini/function-calling code. Module is pure test/harness stand-ins.

## Implementer result
`.workflow/agentic-judgment-10-fake-models/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-10-fake-models/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
