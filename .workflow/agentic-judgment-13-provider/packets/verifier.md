# Fresh-Context Verification Packet — agentic-judgment-13-provider

## Goal

Verify `AgenticJudgmentProvider` is a `JudgmentProvider` drop-in that composes phases 1–3, enforces `evidence_bundle`, raises `AgenticEvidenceGatheringFailedError` on all-sources Phase 1 failure, stamps `session_trace_hash`, and uses an independent Phase 3 budget — without Outcome Matrix orchestrator wiring (Task 14) or PolicyGate changes.

## Acceptance checklist

- [ ] `AgenticJudgmentProvider.generate_judgment` runs `run_source_fanout` → `run_hypothesis_debate` → `run_lead_reconciliation`
- [ ] Missing `request.evidence_bundle` → `ProviderUnavailableError`
- [ ] `fanout_result.all_failed` → `AgenticEvidenceGatheringFailedError` (not generic `Exception`)
- [ ] Success path returns `ModelJudgment` with `session_trace_hash` from `SessionEvidenceRegistry.session_trace_hash()`
- [ ] Phase 3 uses `lead_budget` separate from `source_budget` (no leftover derivation)
- [ ] `ModelJudgment.session_trace_hash` optional field added; single-shot paths unaffected (`None` default)
- [ ] `src/praetor/engine/orchestrator.py` has **no** agentic provider / `AgenticEvidenceGatheringFailedError` wiring
- [ ] `src/praetor/policy/` unchanged by this task
- [ ] Only plan-allowed files changed

## Changed paths

- `src/praetor/contracts/judgment.py`
- `src/praetor/judgment/agentic/provider.py` (new)
- `src/praetor/judgment/agentic/__init__.py`
- `tests/judgment/agentic/test_provider.py` (new)

Implementation result: `results/implementer-result.md`  
Code review: `results/code-review.md` (**PASS**)

## Run (read-only verification)

Set `PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`, then:

```bash
pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -q
ruff check src/praetor/contracts/judgment.py src/praetor/judgment/agentic tests/judgment/agentic
mypy src/praetor/contracts/judgment.py src/praetor/judgment/agentic
```

## Manual checks

1. Read `provider.py` — confirm `lead_budget` is a separate field passed only to `run_lead_reconciliation`.
2. Grep `src/praetor/engine` for `AgenticJudgmentProvider`, `AgenticEvidenceGatheringFailedError`, `agentic` — expect no orchestrator wiring.
3. Grep `src/praetor/policy` diff vs task base — expect no changes from Task 13.
4. Confirm `AgenticEvidenceGatheringFailedError` subclasses `ProviderError` but is **not** yet mapped in orchestrator (Task 14).

Treat prior claims as unevidenced until you run commands and read the diff. Remain read-only except for `results/verifier-result.md`.
