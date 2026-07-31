# agentic-judgment-09-model-protocols

## Goal
Define SourceInvestigatorModel/HypothesisModel/LeadModel Protocols.

## Scope
Protocol surfaces only; no real LLM wire integration.

## Acceptance criteria
- Protocols exist for source investigator, hypothesis, and lead models as specified in the plan.
- Structural protocol tests pass.

## Files allowed
- src/praetor/judgment/agentic/model.py
- tests/judgment/agentic/test_model.py
- .workflow/agentic-judgment-09-model-protocols/

## Verification
- `pytest tests/judgment/agentic/test_model.py -v`
- `ruff check src/praetor/judgment/agentic/model.py tests/judgment/agentic/test_model.py`
- `mypy src/praetor/judgment/agentic/model.py`

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
