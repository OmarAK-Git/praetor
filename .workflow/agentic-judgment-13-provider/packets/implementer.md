# Implementer packet — agentic-judgment-13-provider

## Objective
Compose AgenticJudgmentProvider as a JudgmentProvider drop-in returning session_trace_hash.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/contracts/judgment.py
- src/praetor/judgment/agentic/provider.py
- src/praetor/judgment/agentic/__init__.py
- tests/judgment/agentic/test_provider.py
- .workflow/agentic-judgment-13-provider/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- AgenticJudgmentProvider implements JudgmentProvider and runs phases 1-3.
- All-sources Phase 1 failure raises AgenticEvidenceGatheringFailedError.
- Returned ModelJudgment carries session_trace_hash from the registry.
- Agentic package tests pass.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -q`
- `ruff check src/praetor/contracts/judgment.py src/praetor/judgment/agentic tests/judgment/agentic`
- `mypy src/praetor/contracts/judgment.py src/praetor/judgment/agentic`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
