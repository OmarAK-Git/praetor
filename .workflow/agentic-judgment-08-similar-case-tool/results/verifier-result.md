# Verifier result — agentic-judgment-08-similar-case-tool

**Verdict: PASS**

**Claim checked:** Task 8 is complete — `SimilarCaseTool` wraps `retrieve_similar_case_exemplars`, returns non-evidentiary `ExemplarToolResult` (not `EvidenceFact`/`ToolResult`), and focused tools tests + lint/typechecks pass.

**Single strongest reason it survives:** Fresh commands pass, and independent source + runtime inspection show `invoke` returns only `ExemplarToolResult(exemplars, succeeded, error)` via the existing retrieval helper — no `facts`, no `EvidenceFact`, no provenance on this path.

---

## Evidence gathered (fresh)

### Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)

| Command | Result |
|---------|--------|
| `pytest tests/judgment/agentic/test_tools.py -v` | **11 passed** in 0.88s (includes `test_similar_case_tool_returns_empty_when_no_precedents`, `test_similar_case_tool_rejects_invalid_limit`) |
| `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py` | All checks passed |
| `mypy src/praetor/judgment/agentic/tools.py` | Success: no issues found in 1 source file |

### Focus 1 — Non-evidentiary return type (CRITICAL)

- `ExemplarToolResult` (`tools.py:49-55`): fields `exemplars`, `succeeded`, `error` only — **no** `facts`.
- `SimilarCaseTool.invoke` annotated `-> ExemplarToolResult` (`tools.py:176`).
- `invoke` body: no `EvidenceFact(...)`, no `provenance_path`, no evidence-provenance constants (`tools.py:176-185`).
- Retrieval returns `tuple[dict[str, Any], ...]` (`similar_cases.py:20-39`).

Runtime probe (fresh):

```
type ExemplarToolResult
has_facts False
isinstance_ToolResult False
isinstance_Exemplar True
fields ['exemplars', 'succeeded', 'error']
bad False () 'limit must be a positive int'
EvidenceFact_in_invoke False
provenance_in_invoke False
```

### Focus 2 — Retrieval helper delegation

- Default `limit = arguments.get("limit", MAX_PROMPT_EXEMPLARS)` (`tools.py:177`); `MAX_PROMPT_EXEMPLARS == 3` (runtime).
- Invalid limit → `ExemplarToolResult(exemplars=(), succeeded=False, error="limit must be a positive int")` (`tools.py:178-181`).
- Success path calls `retrieve_similar_case_exemplars(self.conn, evidence_facts=self.evidence_facts, limit=limit)` only (`tools.py:182-184`).
- Tests: empty store → `succeeded is True`, `exemplars == ()` (`test_tools.py:207-215`); `limit: 0` → `succeeded is False` (`test_tools.py:218-222`).

### Focus 3 — Exemplar dict shape

- `_precedent_to_exemplar` keys: `exemplar_id`, `source_case_id`, `summary`, `disposition` (`similar_cases.py:42-48`).
- Task 8 tests cover empty-store / invalid-limit only (plan-prescribed); no positive-path seed in this task.

### Focus 4 — ExemplarCallRecord recordability

- Plan `ExemplarCallRecord` (`docs/superpowers/plans/2026-07-30-agentic-judgment.md:356-364`) and live `registry.py:63-71`: `exemplars`, `succeeded`, `error` (+ metadata `source`/`tool_name`/`query`).
- Task 11 mapping `run_similar_case_source` (`plan.md:2129-2136`) uses `result.exemplars` / `result.error` / `succeeded` — 1:1 with `ExemplarToolResult`; no rename mismatch.

### Focus 5 — Design alignment

- Design spec lines 83–86 / 100: similar cases non-evidentiary illustration-only; implementation docstring (`tools.py:168-170`) and `ExemplarToolResult` match.
- `EXEMPLAR_SCOPE_INSTRUCTIONS` string not present under that name in this worktree `src/`; this task does not alter citation-rejection / exemplar-scope code paths (unchanged by absence of edits).

### Focus 6 — Boundary

- Task 8 deliverable files: `src/praetor/judgment/agentic/tools.py`, `tests/judgment/agentic/test_tools.py`, `.workflow/agentic-judgment-08-similar-case-tool/`.
- No `src/praetor/judgment/agentic/provider.py` (wiring deferred).
- Worktree shows CRLF/status noise on `src/praetor/policy/*` and single-shot `fake_provider.py` / `vertex_provider.py`; `git diff --ignore-cr-at-eol --numstat` empty for those paths — not Task 8 content changes.

---

## Gaps (non-blocking)

1. No positive-path test seeding human-confirmed precedents / asserting exemplar dict keys.
2. Invalid-limit test does not assert `error == "limit must be a positive int"` (implementation does; runtime confirmed).
3. Tests do not assert `not hasattr(result, "facts")` / `not isinstance(result, ToolResult)` (runtime probe does).
4. Identifier `EXEMPLAR_SCOPE_INSTRUCTIONS` not found in `src/`; design intent verified via type boundary + lack of citation-path edits, not a string constant check.

---

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| `SimilarCaseTool` returns exemplar summaries via existing retrieval helper | Met |
| Exemplars remain non-evidentiary (not `EvidenceFacts`) | Met |
| Focused tools tests pass | Met (11/11 + ruff + mypy) |
