# agentic-judgment-08-similar-case-tool

## Goal
Implement SimilarCaseTool wrapping retrieve_similar_case_exemplars.

## Scope
Non-evidentiary exemplar tool only; EXEMPLAR_SCOPE_INSTRUCTIONS semantics unchanged.

## Acceptance criteria
- SimilarCaseTool returns exemplar summaries via existing retrieval helper.
- Exemplars remain non-evidentiary (not EvidenceFacts).
- Focused tools tests pass.

## Files allowed
- src/praetor/judgment/agentic/tools.py
- tests/judgment/agentic/test_tools.py
- .workflow/agentic-judgment-08-similar-case-tool/

## Verification
- `pytest tests/judgment/agentic/test_tools.py -v`
- `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py`
- `mypy src/praetor/judgment/agentic/tools.py`

## Tier
T2

## Researcher decision
skipped: single prescribed implementation path in plan; no multi-path opportunity cost

## Standing orders
- TDD: failing test first, then implement
- Do NOT commit
- Do NOT install dependencies
- Worktree root: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`
- Set `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src` for all python/pytest/mypy
- Single-shot provider / PolicyGate evaluation logic untouched
