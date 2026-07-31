# Verifier packet — agentic-judgment-01-provenance

## Original user goal
Classify ledger_history as non-attacker-controllable provenance (DEC-064).

## Acceptance criteria
- LEDGER_HISTORY constant exists and is_attacker_controllable_provenance(LEDGER_HISTORY) is False.
- Existing WINDOWS_SECURITY_LOG / SYSMON_EVENT_LOG classifications unchanged.
- Unknown provenance paths still default to attacker-controllable.

## Changed files / diff summary
- src/praetor/evidence/provenance.py — added LEDGER_HISTORY; extended _NON_ATTACKER_CONTROLLABLE_PATHS
- tests/evidence/test_provenance.py — new 3 tests

## Verification commands
Worktree: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`
Set `$env:PYTHONPATH = 'C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src'` first.
- `pytest tests/evidence/test_provenance.py -v`
- `ruff check src/praetor/evidence/provenance.py tests/evidence/test_provenance.py`
- `mypy src/praetor/evidence/provenance.py`

## Implementation result path
`.workflow/agentic-judgment-01-provenance/results/implementer-result.md`
Code review: `.workflow/agentic-judgment-01-provenance/results/code-review.md` (PASS)

## Instructions
- Treat implementer claims as unevidenced until checked
- Ignore phase-level or sprint-level gaps (verification.scope is task)
- Write verdict to `.workflow/agentic-judgment-01-provenance/results/verifier-result.md`
- Verdict must be PASS / FAIL / HUMAN_NEEDED with fresh command evidence
