# agentic-judgment-04-request-wiring

## Goal
Thread resolved EvidenceBundle into JudgmentRequest for agentic providers.

## Scope
Optional JudgmentRequest.evidence_bundle field + orchestrator wiring; single-shot path unchanged.

## Acceptance criteria
- JudgmentRequest.evidence_bundle defaults to None and remains backward compatible.
- process_alert_intake passes the resolved EvidenceBundle on JudgmentRequest.
- Existing judgment/engine tests remain green.

## Files allowed
- src/praetor/judgment/provider.py
- src/praetor/engine/orchestrator.py
- tests/judgment/test_provider_failures.py
- tests/engine/test_agentic_request_evidence_bundle_wiring.py
- .workflow/agentic-judgment-04-request-wiring/

## Verification
- `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py tests/judgment tests/engine -q`
- `ruff check src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py tests/engine/test_agentic_request_evidence_bundle_wiring.py`
- `mypy src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py`

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
