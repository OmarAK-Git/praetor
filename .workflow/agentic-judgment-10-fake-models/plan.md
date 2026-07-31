# agentic-judgment-10-fake-models

## Goal
Add deterministic Fake* implementations of the agentic model Protocols.

## Scope
Fake model implementations only; no provider composition yet.

## Acceptance criteria
- FakeSourceInvestigatorModel/FakeHypothesisModel/FakeLeadModel implement the Protocols deterministically.
- Fakes never read EvidenceFact.raw_source.
- Focused fake-model tests pass.

## Files allowed
- src/praetor/judgment/agentic/fake_model.py
- tests/judgment/agentic/test_fake_model.py
- .workflow/agentic-judgment-10-fake-models/

## Verification
- `pytest tests/judgment/agentic/test_fake_model.py -v`
- `ruff check src/praetor/judgment/agentic/fake_model.py tests/judgment/agentic/test_fake_model.py`
- `mypy src/praetor/judgment/agentic/fake_model.py`

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
