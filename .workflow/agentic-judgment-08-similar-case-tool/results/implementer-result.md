# Implementer result — agentic-judgment-08-similar-case-tool

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/agentic/tools.py` | Added `SimilarCaseTool` wrapping `retrieve_similar_case_exemplars`; imports `MAX_PROMPT_EXEMPLARS` and retrieval helper. Returns `ExemplarToolResult` (dict exemplars, not `EvidenceFact`). |
| `tests/judgment/agentic/test_tools.py` | TDD: two tests — empty precedents returns success with empty tuple; invalid `limit` returns failure. |

## TDD sequence

1. Added failing tests importing `SimilarCaseTool` — confirmed `ImportError: cannot import name 'SimilarCaseTool'`.
2. Implemented `SimilarCaseTool` per plan Task 8 spec.
3. All tests pass.

## Verification commands

```
PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src pytest tests/judgment/agentic/test_tools.py -v
```
**Result:** 11 passed in 0.97s

```
PYTHONPATH=... ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py
```
**Result:** All checks passed!

```
PYTHONPATH=... mypy src/praetor/judgment/agentic/tools.py
```
**Result:** Success: no issues found in 1 source file

## Acceptance criteria

- **SimilarCaseTool returns exemplar summaries via existing retrieval helper** — `invoke()` delegates to `retrieve_similar_case_exemplars(conn, evidence_facts=..., limit=...)`.
- **Exemplars remain non-evidentiary** — returns `ExemplarToolResult` with `tuple[dict[str, Any], ...]`, not `EvidenceFact`.
- **Focused tools tests pass** — 11/11 green.

## Gaps / notes

- Plan referenced `praetor.annotations.state.init_annotations_schema` (does not exist); tests use `open_state_store` which already calls `init_annotation_schema` — consistent with other tests in `test_tools.py`.
- No commit per standing orders.
- Task 12 (`provider.py`) wiring deferred to later task.
