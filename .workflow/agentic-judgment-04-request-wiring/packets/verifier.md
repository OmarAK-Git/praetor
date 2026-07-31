# Verifier packet — agentic-judgment-04-request-wiring

## Goal
Thread resolved EvidenceBundle into JudgmentRequest for agentic providers.

## Acceptance criteria
- `JudgmentRequest.evidence_bundle` defaults to `None` and remains backward compatible.
- `process_alert_intake` passes the resolved `EvidenceBundle` on `JudgmentRequest`.
- Existing judgment/engine tests remain green.

## Changed files
- `src/praetor/judgment/provider.py`
- `src/praetor/engine/orchestrator.py`
- `tests/judgment/test_provider_failures.py`
- `tests/engine/test_agentic_request_evidence_bundle_wiring.py` (new, untracked)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py tests/judgment tests/engine -q`
- `ruff check src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py tests/engine/test_agentic_request_evidence_bundle_wiring.py`
- `mypy src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py`

## Focus checks (skeptic)
1. **Backward compat:** Construct `JudgmentRequest(scenario_id="x")` without `evidence_bundle`; confirm default `None`. Spot-check existing single-shot tests still pass without passing the new field.
2. **Orchestrator wiring:** In `test_process_alert_intake_passes_evidence_bundle_on_request`, confirm captured request has non-`None` `evidence_bundle` whose facts match the intake bundle.
3. **PolicyGate untouched:** `git diff HEAD -- src/praetor/policy/` must show no content changes; `evaluate_policy_gate` call in `orchestrator.py` unchanged except unrelated context.
4. **Scope:** No edits to `FakeProvider` / `VertexProvider` implementation; single-shot behavior unchanged.

## Implementer result
`.workflow/agentic-judgment-04-request-wiring/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-04-request-wiring/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
