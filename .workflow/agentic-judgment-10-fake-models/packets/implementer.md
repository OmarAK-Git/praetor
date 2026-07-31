# Implementer packet — agentic-judgment-10-fake-models

## Objective
Add deterministic Fake* implementations of the agentic model Protocols.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/judgment/agentic/fake_model.py
- tests/judgment/agentic/test_fake_model.py
- .workflow/agentic-judgment-10-fake-models/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- FakeSourceInvestigatorModel/FakeHypothesisModel/FakeLeadModel implement the Protocols deterministically.
- Fakes never read EvidenceFact.raw_source.
- Focused fake-model tests pass.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/judgment/agentic/test_fake_model.py -v`
- `ruff check src/praetor/judgment/agentic/fake_model.py tests/judgment/agentic/test_fake_model.py`
- `mypy src/praetor/judgment/agentic/fake_model.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
