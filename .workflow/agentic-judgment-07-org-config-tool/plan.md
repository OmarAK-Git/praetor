# agentic-judgment-07-org-config-tool

## Goal
Implement OrgConfigSectionTool (non-evidentiary org_config_refs path).

## Scope
Org-config section tool only; must not feed corroboration/cited_evidence_refs.

## Acceptance criteria
- OrgConfigSectionTool returns section text for named sections without producing EvidenceFacts.
- Tool results are recordable as OrgConfigCallRecord entries.
- Focused tools tests pass.

## Files allowed
- src/praetor/judgment/agentic/tools.py
- tests/judgment/agentic/test_tools.py
- .workflow/agentic-judgment-07-org-config-tool/

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
