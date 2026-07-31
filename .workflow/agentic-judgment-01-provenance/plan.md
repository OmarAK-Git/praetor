# agentic-judgment-01-provenance

## Goal
Classify ledger_history as non-attacker-controllable provenance (DEC-064).

## Scope
Provenance trust table only; no PolicyGate logic changes.

## Acceptance criteria
- LEDGER_HISTORY constant exists and is_attacker_controllable_provenance(LEDGER_HISTORY) is False.
- Existing WINDOWS_SECURITY_LOG / SYSMON_EVENT_LOG classifications unchanged.
- Unknown provenance paths still default to attacker-controllable.

## Files allowed
- src/praetor/evidence/provenance.py
- tests/evidence/test_provenance.py
- .workflow/agentic-judgment-01-provenance/

## Verification
- `pytest tests/evidence/test_provenance.py -v`
- `ruff check src/praetor/evidence/provenance.py tests/evidence/test_provenance.py`
- `mypy src/praetor/evidence/provenance.py`

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
