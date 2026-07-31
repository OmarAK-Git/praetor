# Verifier packet — agentic-judgment-08-similar-case-tool

## Goal
Implement `SimilarCaseTool` wrapping `retrieve_similar_case_exemplars` — **non-evidentiary** exemplar summaries only; `EXEMPLAR_SCOPE_INSTRUCTIONS` semantics unchanged.

## Acceptance criteria
- `SimilarCaseTool` returns exemplar summaries via existing retrieval helper.
- Exemplars remain non-evidentiary (not `EvidenceFacts`).
- Focused tools tests pass.

## Changed files
- `src/praetor/judgment/agentic/tools.py` — `SimilarCaseTool` appended (file also contains Task 6/7 tools); imports `MAX_PROMPT_EXEMPLARS`, `retrieve_similar_case_exemplars`
- `tests/judgment/agentic/test_tools.py` — two similar-case tests appended (file also contains Task 6/7 tests)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_tools.py -v`
- `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py`
- `mypy src/praetor/judgment/agentic/tools.py`

## Focus checks (skeptic)

### 1. Non-evidentiary return type (CRITICAL — no corroboration path)
In `src/praetor/judgment/agentic/tools.py`, confirm `SimilarCaseTool.invoke` return annotation is `ExemplarToolResult`, **not** `ToolResult`.

Confirm `ExemplarToolResult` (`tools.py:49-55`) has fields `exemplars`, `succeeded`, `error` only — **no** `facts` field.

Confirm `SimilarCaseTool.invoke` body contains **no** `EvidenceFact(...)` construction, **no** `provenance_path` assignment, and **no** import/use of evidence provenance constants for this tool.

Confirm `exemplars` payload is `tuple[dict[str, Any], ...]` from `retrieve_similar_case_exemplars` (`similar_cases.py:20-39`), not `EvidenceFact` objects.

Runtime spot-check (optional):
```python
from praetor.judgment.agentic.tools import SimilarCaseTool, ExemplarToolResult, ToolResult
from praetor.state.store import open_state_store
# after open_state_store(tmp_path / "probe.db"):
r = tool.invoke({})
assert type(r).__name__ == "ExemplarToolResult"
assert not hasattr(r, "facts")
assert not isinstance(r, ToolResult)
```

**Do not** treat exemplar output as citable evidence or corroboration-eligible in verification reasoning. Exemplars are illustration-only per design spec line 100.

### 2. Retrieval helper delegation
Confirm `invoke` calls `retrieve_similar_case_exemplars(self.conn, evidence_facts=self.evidence_facts, limit=limit)` (`tools.py:182-184`) — no alternate ranking or precedent-fetch path.

Confirm default `limit` is `MAX_PROMPT_EXEMPLARS` when argument omitted (`tools.py:177`).

Confirm invalid `limit` (`not isinstance(limit, int) or limit < 1`) returns failed `ExemplarToolResult` with empty exemplars and error `"limit must be a positive int"` (`tools.py:177-181`).

`test_similar_case_tool_returns_empty_when_no_precedents` must assert `succeeded is True` and `exemplars == ()`.

`test_similar_case_tool_rejects_invalid_limit` must assert `succeeded is False` for `limit: 0`.

### 3. Exemplar dict shape (when precedents exist)
Read `_precedent_to_exemplar` in `src/praetor/retrieval/similar_cases.py:42-48`. Exemplar dict keys: `exemplar_id`, `source_case_id`, `summary`, `disposition`. Task 8 tests cover empty-store only; if adding a positive-path probe, use existing precedent-fixture patterns from judgment retrieval tests — do not treat exemplar content as evidence in verification.

### 4. ExemplarCallRecord recordability (structural)
Read `ExemplarCallRecord` definition in plan `docs/superpowers/plans/2026-07-30-agentic-judgment.md` (~356-374). Confirm tool result fields map 1:1 to `exemplars`, `succeeded`, `error` (call metadata `source`/`tool_name`/`query` added by Task 11 provider wiring, not this task).

Cross-check plan Task 11 `run_similar_case_source` mapping (~2120-2138). No field rename or type mismatch.

### 5. Design alignment (non-evidentiary / EXEMPLAR_SCOPE unchanged)
Read design spec `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` lines 83–86 and 100. Confirm implementation docstring and result type match: similar cases are agent-queried human-confirmed precedents, explicitly non-evidentiary; exemplar citation rejection semantics are unchanged by this task.

### 6. Boundary / untouched paths
- No changes under `src/praetor/policy/`.
- No changes to `VertexProvider` / `FakeProvider` single-shot behavior.
- No provider wiring in this task (deferred to Task 12).
- Production changes for this task confined to `files_allowed`.

## Implementer result
`.workflow/agentic-judgment-08-similar-case-tool/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-08-similar-case-tool/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
