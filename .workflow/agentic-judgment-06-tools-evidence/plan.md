# agentic-judgment-06-tools-evidence

## Goal
Implement LedgerHistoryTool and WiderTelemetryTool with raw_source isolation.

## Scope
Evidence-producing tools only; org-config and similar-case tools come later.

## Acceptance criteria
- LedgerHistoryTool returns EvidenceFacts with provenance_path=ledger_history and never leaks raw_source.
- WiderTelemetryTool re-fetches untruncated facts from the request EvidenceBundle using existing provenance paths.
- Scope constraints from the design are enforced in tests.

## Files allowed
- src/praetor/judgment/agentic/tools.py
- tests/judgment/agentic/test_tools.py
- .workflow/agentic-judgment-06-tools-evidence/

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
