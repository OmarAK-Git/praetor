# Implementer packet — agentic-judgment-14-outcome-matrix

## Objective
Register agentic_evidence_gathering_failed, thread session_trace_hash into DecisionEdict, and update docs.

## Original user goal
Implement from docs/superpowers/plans/2026-07-30-agentic-judgment.md per docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.

## Relevant docs
- docs/superpowers/plans/2026-07-30-agentic-judgment.md
- docs/superpowers/specs/2026-07-30-agentic-judgment-design.md
- .workflow/_dream/playbook.digest.md
- this run plan.md

## Allowed files
- src/praetor/metrics/events.py
- src/praetor/contracts/fault_flags.py
- src/praetor/contracts/edict.py
- src/praetor/engine/orchestrator.py
- src/praetor/engine/edict.py
- src/praetor/judgment/fake_provider.py
- evals/harness.py
- evals/scenarios/agentic_evidence_gathering_failed.yaml
- docs/decisions.md
- docs/contracts.md
- docs/architecture.md
- tests/engine/test_agentic_evidence_gathering_failed_intake.py
- tests/contracts/test_edict_session_trace_hash.py
- tests/engine/test_edict_session_trace_hash.py
- tests/evals/test_eval_harness.py
- tests/contracts/test_scope_guard.py
- .workflow/agentic-judgment-14-outcome-matrix/
- schemas/
- tools/schema_export.py

## Do not touch
- Anything outside files_allowed
- src/praetor/policy/ evaluation logic
- Single-shot VertexProvider/FakeProvider behavior except when this task explicitly lists FakeProvider

## Acceptance criteria
- AgenticEvidenceGatheringFailedError maps to escalate with agentic_evidence_gathering_failed and system_fault_escalation=true without tripping the provider-health breaker.
- DecisionEdict.session_trace_hash is optional and copied from ModelJudgment.
- Outcome Matrix completeness guard passes with the new harness scenario.
- DEC-064 and contracts/architecture docs updated; PolicyGate evaluation files unchanged.
- Committed schemas regenerated for session_trace_hash (model_judgment + decision_edict); schema export --check passes.

## Verification commands
(run with PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src)
- `pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py tests/evals/test_eval_harness.py tests/contracts/test_edict_session_trace_hash.py -q`
- `ruff check src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine src/praetor/judgment/fake_provider.py evals tests/engine/test_agentic_evidence_gathering_failed_intake.py`
- `mypy src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine/orchestrator.py src/praetor/judgment/fake_provider.py`
- `python tools/schema_export.py --check`

## Expected result schema
Write results/implementer-result.md: files changed, commands+outcomes, gaps.

## Mandatory
- Follow the matching plan Task steps exactly (TDD)
- Do NOT mark queue item done
- Do NOT commit
- Do NOT run phase/sprint exit verification unless this item is phase_exit
- Stop before approval gates
