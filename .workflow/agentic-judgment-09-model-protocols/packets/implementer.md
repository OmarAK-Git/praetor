# Implementer packet — agentic-judgment-09-model-protocols

## Objective
Define SourceInvestigatorModel/HypothesisModel/LeadModel Protocols.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/judgment/agentic/model.py
- tests/judgment/agentic/test_model.py
- .workflow/agentic-judgment-09-model-protocols/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- Protocols exist for source investigator, hypothesis, and lead models as specified in the plan.
- Structural protocol tests pass.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/judgment/agentic/test_model.py -v`
- `ruff check src/praetor/judgment/agentic/model.py tests/judgment/agentic/test_model.py`
- `mypy src/praetor/judgment/agentic/model.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
