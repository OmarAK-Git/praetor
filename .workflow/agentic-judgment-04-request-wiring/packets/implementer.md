# Implementer packet — agentic-judgment-04-request-wiring

## Objective
Thread resolved EvidenceBundle into JudgmentRequest for agentic providers.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/judgment/provider.py
- src/praetor/engine/orchestrator.py
- tests/judgment/test_provider_failures.py
- tests/engine/test_agentic_request_evidence_bundle_wiring.py
- .workflow/agentic-judgment-04-request-wiring/

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- JudgmentRequest.evidence_bundle defaults to None and remains backward compatible.
- process_alert_intake passes the resolved EvidenceBundle on JudgmentRequest.
- Existing judgment/engine tests remain green.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py tests/judgment tests/engine -q`
- `ruff check src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py tests/engine/test_agentic_request_evidence_bundle_wiring.py`
- `mypy src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
