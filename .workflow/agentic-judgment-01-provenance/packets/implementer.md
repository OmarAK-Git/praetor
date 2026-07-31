# Implementer packet — agentic-judgment-01-provenance

## Objective
Classify ledger_history as non-attacker-controllable provenance (DEC-064).

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/evidence/provenance.py
- tests/evidence/test_provenance.py
- .workflow/agentic-judgment-01-provenance/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- LEDGER_HISTORY constant exists and is_attacker_controllable_provenance(LEDGER_HISTORY) is False.
- Existing WINDOWS_SECURITY_LOG / SYSMON_EVENT_LOG classifications unchanged.
- Unknown provenance paths still default to attacker-controllable.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/evidence/test_provenance.py -v`
- `ruff check src/praetor/evidence/provenance.py tests/evidence/test_provenance.py`
- `mypy src/praetor/evidence/provenance.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
