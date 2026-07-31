# Code Review — agentic-judgment-13-provider

**Verdict: PASS**

**Scope:** `AgenticJudgmentProvider` composition + `ModelJudgment.session_trace_hash`  
**Plan:** `.workflow/agentic-judgment-13-provider/plan.md`  
**Implementer result:** `.workflow/agentic-judgment-13-provider/results/implementer-result.md`

## Summary

Task 13 delivers a structurally conformant `JudgmentProvider` that runs phases 1–3, requires `evidence_bundle`, raises `AgenticEvidenceGatheringFailedError` on all-sources Phase 1 failure, stamps `session_trace_hash` from the session registry, and keeps Phase 3 on an independent `lead_budget`. Orchestrator / Outcome Matrix wiring and PolicyGate are correctly untouched (Task 14).

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| `AgenticJudgmentProvider` implements `JudgmentProvider` and runs phases 1–3 | Met — `generate_judgment` calls `run_source_fanout` → `run_hypothesis_debate` → `run_lead_reconciliation` (`provider.py:103–130`) |
| All-sources Phase 1 failure raises `AgenticEvidenceGatheringFailedError` | Met — guarded at `provider.py:115–117`; test `test_generate_judgment_raises_when_all_sources_fail` |
| Returned `ModelJudgment` carries `session_trace_hash` from registry | Met — `model_copy(update={"session_trace_hash": registry.session_trace_hash()})` at `provider.py:131–136`; e2e test asserts non-None 64-char hash |
| Agentic package tests pass | Met — fresh re-run: **44 passed** (see Verification) |
| `evidence_bundle` required | Met — `ProviderUnavailableError` when missing (`provider.py:72–74`); dedicated test |
| Independent Phase 3 budget | Met — separate `lead_budget` field/default (`provider.py:41–42, 69, 128–129`); not derived from Phase 1/2 trackers |
| Outcome Matrix NOT wired (Task 14) | Met — no `AgenticJudgmentProvider` / `AgenticEvidenceGatheringFailedError` references under `src/praetor/engine/` |
| PolicyGate untouched | Met — no changes under `src/praetor/policy/` in task scope |

**Allowed files only:** `contracts/judgment.py`, `judgment/agentic/provider.py`, `judgment/agentic/__init__.py`, `tests/judgment/agentic/test_provider.py`, workflow artifacts.

## Focus-area audit

### JudgmentProvider conformance

- Implements `generate_judgment(JudgmentRequest) -> ModelJudgment` and `probe(...) -> ProviderProbeResult` matching `JudgmentProvider` in `judgment/provider.py:77–82`.
- `probe` is lightweight and does not touch DB (`provider.py:139–145`); covered by `test_probe_reports_success`.

### All-sources-fail → `AgenticEvidenceGatheringFailedError`

- Uses `SourceFanoutResult.all_failed` from phases layer (`phases.py:169–176`).
- Error subclasses `ProviderError` (`errors.py:8–9`), ready for Task 14 Outcome Matrix mapping; correctly **not** caught in orchestrator yet.

### Independent Phase 3 budget

- `DEFAULT_LEAD_BUDGET = PhaseBudget(max_tool_calls=0, max_seconds=15.0)` is separate from `DEFAULT_SOURCE_BUDGET`.
- `run_lead_reconciliation` receives `budget=self.lead_budget` only; Phase 1 fan-out uses `self.source_budget`. No shared `BudgetTracker` or leftover arithmetic.

### `session_trace_hash`

- Optional field added to `ModelJudgment` with `None` default (`contracts/judgment.py:28–31`) — backward compatible for single-shot paths.
- Provider overwrites via `model_copy` after Phase 3 completes.

### `evidence_bundle` required

- Early guard before scope resolution or snapshot fetch.

### Outcome Matrix / PolicyGate boundary

- Orchestrator still maps only the four existing `ProviderError` subclasses (`orchestrator.py:379–410`); no agentic imports.
- Policy evaluation code unchanged — correct per standing orders.

## Correctness

- `_resolve_scope` derives `allowed_target_ids` from bundle facts with `host_id` (`provider.py:45–53`).
- Org-config snapshot resolved via `fetch_snapshot_by_hash`; missing snapshot → `ProviderUnavailableError` (config/precondition, not Phase 1 gather failure) — reasonable.
- Phase 1 thread fan-out requires `check_same_thread=False` in tests only; production connection policy unchanged (documented in implementer-result).

## Security

- Tools scoped via `alert_reference` + `allowed_target_ids` from evidence bundle; no widening beyond prior phase/tool tasks.
- No secrets, unsafe deserialization, or new trust boundaries.

## Simplicity

- Provider is a thin composition layer over existing phases/registry/tools — appropriate for Task 13.
- Minor: `assert request.evidence_bundle is not None` in `_resolve_scope` (`provider.py:46`) is redundant given the upstream guard; prefer unreachable comment or drop assert (non-blocking).

## Tests

Fresh re-run (reviewer, `PYTHONPATH=.../src`):

| Command | Result |
|---|---|
| `pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -q` | **44 passed** |
| `ruff check src/praetor/contracts/judgment.py src/praetor/judgment/agentic tests/judgment/agentic` | All checks passed |
| `mypy src/praetor/contracts/judgment.py src/praetor/judgment/agentic` | Success: 10 files |

Provider tests cover: missing bundle, e2e happy path, all-sources-fail, probe.

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

| Location | Issue | Suggested fix |
|---|---|---|
| `tests/judgment/agentic/test_provider.py` | No assertion that `judgment.session_trace_hash == registry.session_trace_hash()` (only length check) | Optional: capture registry in a spy or recompute expected hash in e2e test |
| `tests/judgment/agentic/test_provider.py` | Phase 3 budget independence not exercised (e.g. exhaust Phase 1 budget, assert Phase 3 still receives full `lead_budget`) | Optional regression test in Task 14 or follow-up |
| `provider.py:46` | Redundant `assert` on `evidence_bundle` | Remove assert or replace with explicit `raise` if keeping helper public |

## Verdict rationale

All plan acceptance criteria and user focus constraints are met. Implementation is correct, scoped, and verified. Orchestrator/Outcome Matrix deferral and PolicyGate isolation are as required. No Critical or Important defects. **PASS** — ready for skeptic-verify.
