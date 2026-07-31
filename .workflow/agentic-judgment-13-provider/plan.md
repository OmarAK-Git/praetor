# agentic-judgment-13-provider

## Goal
Compose AgenticJudgmentProvider as a JudgmentProvider drop-in returning session_trace_hash.

## Scope
Provider composition + ModelJudgment.session_trace_hash field; no Outcome Matrix wiring yet.

## Acceptance criteria
- AgenticJudgmentProvider implements JudgmentProvider and runs phases 1-3.
- All-sources Phase 1 failure raises AgenticEvidenceGatheringFailedError.
- Returned ModelJudgment carries session_trace_hash from the registry.
- Agentic package tests pass.

## Files allowed
- src/praetor/contracts/judgment.py
- src/praetor/judgment/agentic/provider.py
- src/praetor/judgment/agentic/__init__.py
- tests/judgment/agentic/test_provider.py
- .workflow/agentic-judgment-13-provider/

## Verification
- `pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -q`
- `ruff check src/praetor/contracts/judgment.py src/praetor/judgment/agentic tests/judgment/agentic`
- `mypy src/praetor/contracts/judgment.py src/praetor/judgment/agentic`

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
