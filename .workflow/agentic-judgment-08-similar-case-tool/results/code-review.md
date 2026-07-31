# Code review — agentic-judgment-08-similar-case-tool

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 8 — `SimilarCaseTool` (non-evidentiary exemplar retrieval)  
**Spec:** `.workflow/agentic-judgment-08-similar-case-tool/plan.md`  
**Design:** `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` (tool table lines 83–86, non-evidentiary boundary line 100)

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | `src/praetor/judgment/agentic/tools.py` — `SimilarCaseTool` + `ExemplarToolResult` (untracked; appended to Task 6/7 file) |
| Tests | `tests/judgment/agentic/test_tools.py` — two new similar-case tests (untracked; appended to Task 6/7 file) |
| Diff baseline | Matches Task 8 Step 3 in `docs/superpowers/plans/2026-07-30-agentic-judgment.md` verbatim |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_tools.py -v` → **11 passed** in 0.92s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| Return-type probe | `invoke({})` → `ExemplarToolResult`, `hasattr(result, "facts")` is **False**, `isinstance(result, ToolResult)` is **False** |
| PolicyGate / provider | No changes outside `files_allowed` |

---

## Focus-area review

### 1. Non-evidentiary boundary (no EvidenceFacts / corroboration path) — PASS

`SimilarCaseTool.invoke` returns `ExemplarToolResult` (`tools.py:176-185`), not `ToolResult`. The result dataclass (`tools.py:49-55`) exposes only `exemplars`, `succeeded`, `error` — no `facts` field.

`invoke` delegates to `retrieve_similar_case_exemplars` (`tools.py:182-184`), which returns `tuple[dict[str, Any], ...]` (`similar_cases.py:20-39`). No `EvidenceFact(...)` construction, no `provenance_path` assignment, no evidence provenance constants on this path.

Docstring (`tools.py:168-170`) states same source as today's fixed top-3 exemplars and explicitly non-evidentiary — aligned with design spec line 100 (`EXEMPLAR_SCOPE_INSTRUCTIONS` semantics unchanged; exemplar citations remain rejected).

### 2. Retrieval helper delegation / limit validation — PASS

Unknown or invalid `limit` (`not isinstance(limit, int) or limit < 1`) → failed `ExemplarToolResult` with empty exemplars and descriptive error (`tools.py:177-181`). Default `limit` is `MAX_PROMPT_EXEMPLARS` (`tools.py:177`).

Valid invoke path passes `conn`, `evidence_facts`, and `limit` through to `retrieve_similar_case_exemplars` unchanged — matches prescribed plan Step 3.

`test_similar_case_tool_returns_empty_when_no_precedents` exercises empty-store path with `succeeded is True` and `exemplars == ()`. `test_similar_case_tool_rejects_invalid_limit` asserts `succeeded is False` for `limit: 0`.

### 3. ExemplarCallRecord recordability — PASS (structural)

`ExemplarCallRecord` (`plan.md:356-374`; registry deferred to Task 2) fields: `exemplars`, `succeeded`, `error` plus call metadata. Task 11 `run_similar_case_source` maps tool result fields directly (`plan.md:2128-2137`). Field names and types align; no adapter needed.

### 4. Scope / untouched paths — PASS

Changes confined to `files_allowed`. Test setup uses `open_state_store`, which already calls `init_annotation_schema` and `init_ledger_schema` (`store.py:354-363`) — acceptable deviation from plan Step 1's nonexistent `praetor.annotations.state.init_annotations_schema` import (noted in implementer result).

PolicyGate and single-shot provider paths untouched. Provider wiring deferred to Task 12 per plan.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_tools.py`** — No explicit assertion that `ExemplarToolResult` lacks a `.facts` attribute or is not a `ToolResult` subclass. Type separation is enforced by implementation and mypy; runtime probe confirms behavior.

2. **`tests/judgment/agentic/test_tools.py`** — No test seeding human-confirmed precedents and asserting non-empty exemplar dict shape (`exemplar_id`, `source_case_id`, `summary`, `disposition` per `similar_cases.py:42-48`). Empty-store and invalid-limit paths only.

3. **`tests/judgment/agentic/test_tools.py:218-222`** — Invalid-limit test does not assert `error` message content (`"limit must be a positive int"`).

4. **`tests/judgment/agentic/test_tools.py`** — Non-int `limit` values (e.g. `"3"`, `3.0`) are rejected by implementation but untested.

5. **`tools.py:182-184`** — `retrieve_similar_case_exemplars` supports `exclude_decision_id`; tool does not expose it. Plan Step 3 does not require it; defer unless Task 12 provider needs it.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `SimilarCaseTool` returns exemplar summaries via existing retrieval helper | Met — `invoke` delegates to `retrieve_similar_case_exemplars` |
| Exemplars remain non-evidentiary (not `EvidenceFacts`) | Met — `ExemplarToolResult` with `tuple[dict[str, Any], ...]` only |
| Focused tools tests pass | Met — 11/11 pytest, ruff, mypy |
| `EXEMPLAR_SCOPE_INSTRUCTIONS` semantics unchanged | Met — no changes to exemplar scope or citation validation in this task |
| Files allowed only | Met |
| PolicyGate / single-shot provider untouched | Met |

---

## Correctness / security / simplicity

- **Correctness:** Limit guard runs before retrieval call. Empty precedent set returns success with empty tuple (consistent with retrieval helper). `evidence_facts` typed as `tuple[Mapping[str, Any], ...]` matches retrieval helper's `Iterable[Mapping[str, Any]]` contract.
- **Security:** Read-only query over existing human-confirmed precedent store; no user-controlled SQL. Output is summary dicts, not raw log content or citable evidence.
- **Simplicity:** Implementation is plan-prescribed verbatim; reuses existing retrieval helper and `ExemplarToolResult` stub from Task 6. No duplicate exemplar-fetch logic.

---

## Summary

Task 8 implementation matches the approved plan and design boundary: similar-case fetches are non-evidentiary illustration-only output, never enter the `EvidenceFact` or corroboration path, and map cleanly to deferred `ExemplarCallRecord` wiring. Minor test gaps do not block verification. Proceed to skeptic verification.
