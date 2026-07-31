# Code review — agentic-judgment-09-model-protocols

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 9 — model-calling Protocols and result dataclasses  
**Spec:** `.workflow/agentic-judgment-09-model-protocols/plan.md`  
**Design:** `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 9 (lines 1523–1659)

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | `src/praetor/judgment/agentic/model.py` (untracked, new) |
| Tests | `tests/judgment/agentic/test_model.py` (untracked, new) |
| Diff baseline | Matches Task 9 Step 3 in `docs/superpowers/plans/2026-07-30-agentic-judgment.md` verbatim (only cosmetic signature wrap for ruff E501) |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_model.py -v` → **3 passed** in 0.26s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| PolicyGate / provider | No changes outside `files_allowed` |

---

## Focus-area review

### 1. Spec compliance — PASS

All prescribed surfaces present in `model.py`:

| Surface | Location | Status |
|---------|----------|--------|
| `ToolCallDecision(arguments: dict[str, Any])` | `model.py:22-26` | Present, `frozen=True` |
| `InvestigationSummary(narrative: str)` | `model.py:29-33` | Present, `frozen=True` |
| `HypothesisCase(stance, key_points, cited_evidence_ids, narrative)` | `model.py:36-41` | Present; tuple fields for immutability |
| `SourceInvestigatorModel.next_action(*, prior_call_count, last_call_succeeded) -> ToolCallDecision \| InvestigationSummary` | `model.py:44-49` | Present, `@runtime_checkable` |
| `HypothesisModel.build_case(*, stance, registry_facts, budget) -> HypothesisCase` | `model.py:52-61` | Present, `@runtime_checkable` |
| `LeadModel.reconcile(*, registry_facts, malicious_case, benign_case, budget) -> ModelJudgment` | `model.py:64-74` | Present, `@runtime_checkable` |

Imports align with plan: `EvidenceFact`, `ModelJudgment`, `PhaseBudget`. No LLM wire integration (explicitly out of scope).

Tests match Task 9 Step 1 exactly (3 dataclass structural tests). Protocol `isinstance` conformance is correctly deferred to Task 10 (`fake_model.py`).

### 2. Correctness — PASS

- Return types and keyword-only parameters match the orchestration contract Task 11 (`phases.py`) will consume.
- `last_call_succeeded: bool | None` correctly models the first-call (`None`) vs subsequent-call distinction.
- `Sequence[EvidenceFact]` for `registry_facts` is appropriate for read-only fan-in from `SessionEvidenceRegistry`.
- `HypothesisCase` uses `tuple[str, ...]` for `key_points` and `cited_evidence_ids`, preventing accidental in-place mutation of case content.

### 3. Security — PASS

- Protocol surface only; no I/O, deserialization, or prompt assembly.
- No `raw_source` exposure path introduced (DEC-047 isolation enforced structurally in later tasks).
- No policy or provider changes.

### 4. Simplicity — PASS

- Implementation is plan-prescribed verbatim; no speculative abstractions or duplicate protocol definitions elsewhere in `praetor.judgment.agentic`.
- Module docstring correctly documents the seam role and defers real backend to follow-on work.

### 5. Tests — PASS (within Task 9 scope)

- Three tests exercise dataclass construction and field retention.
- Tests would fail without the module (TDD red phase confirmed by implementer).
- Protocol structural conformance not tested here — by design per plan; Task 10 owns fake implementations + `isinstance` checks.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_model.py:12-14`** — `test_tool_call_decision_is_frozen` checks field values only; it does not assert immutability (e.g. `pytest.raises(FrozenInstanceError)` on attribute assignment). Name is slightly misleading; matches plan Step 1 verbatim.

2. **`tests/judgment/agentic/test_model.py:22-31`** — `test_hypothesis_case_fields` asserts `stance` and `key_points` only; does not assert `cited_evidence_ids` or `narrative`. Matches plan Step 1 verbatim.

3. **`model.py:26`** — `ToolCallDecision.arguments` is `dict[str, Any]` inside a frozen dataclass; the dict object remains mutable if a caller retains a reference. Plan-prescribed; acceptable for Task 9 seam (Task 10 fakes copy via `dict(...)`).

4. **`model.py:54-60`** — `HypothesisModel.build_case` signature wrapped across lines for ruff E501; semantically identical to plan.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| Protocols exist for source investigator, hypothesis, and lead models | Met — all three `@runtime_checkable` Protocols present |
| Structural protocol tests pass | Met — 3/3 pytest, ruff, mypy |
| Protocol surfaces only; no real LLM wire integration | Met |
| Files allowed only | Met — only `model.py`, `test_model.py`, workflow dir touched |
| PolicyGate / single-shot provider untouched | Met |

---

## Correctness / security / simplicity

- **Correctness:** Types and signatures match Task 9 interfaces table and Task 10/11 consumer contracts.
- **Security:** No runtime behavior; pure type seam.
- **Simplicity:** Minimal, plan-faithful module with no dead code.

---

## Summary

Task 9 delivers the prescribed model-calling Protocol seam and frozen result dataclasses exactly as specified. Verification commands pass on fresh run. Minor test naming/coverage gaps mirror the plan text and do not block Task 10. Proceed to skeptic verification.
