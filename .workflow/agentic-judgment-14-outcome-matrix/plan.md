# agentic-judgment-14-outcome-matrix

## Goal
Register agentic_evidence_gathering_failed, thread session_trace_hash into DecisionEdict, and update docs.

## Scope
Fault flag + orchestrator catch + edict field + harness scenario + DEC-064 docs; PolicyGate logic untouched.

## Acceptance criteria
- AgenticEvidenceGatheringFailedError maps to escalate with agentic_evidence_gathering_failed and system_fault_escalation=true without tripping the provider-health breaker.
- DecisionEdict.session_trace_hash is optional and copied from ModelJudgment.
- Outcome Matrix completeness guard passes with the new harness scenario.
- DEC-064 and contracts/architecture docs updated; PolicyGate evaluation files unchanged.
- Committed schemas regenerated for session_trace_hash (model_judgment + decision_edict); schema export --check passes.

## Files allowed
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

## Verification
- `pytest tests/engine/test_agentic_evidence_gathering_failed_intake.py tests/evals/test_eval_harness.py tests/contracts/test_edict_session_trace_hash.py -q`
- `ruff check src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine src/praetor/judgment/fake_provider.py evals tests/engine/test_agentic_evidence_gathering_failed_intake.py`
- `mypy src/praetor/metrics/events.py src/praetor/contracts src/praetor/engine/orchestrator.py src/praetor/judgment/fake_provider.py`
- `python tools/schema_export.py --check`

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
