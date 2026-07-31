# Skeptic-verifier result — agentic-judgment-13-provider

## Claim restated

`AgenticJudgmentProvider` is a `JudgmentProvider` drop-in that composes Phase 1–3 (`run_source_fanout` → `run_hypothesis_debate` → `run_lead_reconciliation`), requires `request.evidence_bundle`, raises `AgenticEvidenceGatheringFailedError` when `fanout_result.all_failed`, stamps `ModelJudgment.session_trace_hash` from `SessionEvidenceRegistry.session_trace_hash()`, uses an independent Phase 3 `lead_budget` (not leftover-derived), adds optional `session_trace_hash` with `None` default for single-shot paths, and does **not** wire Outcome Matrix / orchestrator or change PolicyGate (Task 14). Only plan-allowed files are in Task 13 scope.

## Verdict

**survives**

## Evidence gathered (fresh, this run)

### Commands

| Command | Outcome |
|---|---|
| `PYTHONPATH=.../src pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -q` | **44 passed** in 1.61s |
| `ruff check src/praetor/contracts/judgment.py src/praetor/judgment/agentic tests/judgment/agentic` | All checks passed |
| `mypy src/praetor/contracts/judgment.py src/praetor/judgment/agentic` | Success: no issues found in 10 source files |
| `pytest .../test_provider.py::test_generate_judgment_end_to_end_with_fakes -vv` | PASSED |
| Runtime: `isinstance(AgenticJudgmentProvider(...), JudgmentProvider)` | `True` |
| Runtime: `issubclass(AgenticEvidenceGatheringFailedError, ProviderError)` | `True` |
| Runtime: `skeleton_model_judgment().session_trace_hash is None` | `True` |
| Runtime replay of e2e path | SUCCESS; returned 64-char hex `session_trace_hash`, `provider_name=agentic` |

### Manual / code reads

| Check | Evidence |
|---|---|
| Phase composition | `provider.py:103–130` calls fan-out → debate → lead reconciliation in order |
| Missing `evidence_bundle` | `provider.py:72–74` raises `ProviderUnavailableError`; covered by `test_generate_judgment_requires_evidence_bundle` |
| `all_failed` → typed error | `provider.py:115–117` raises `AgenticEvidenceGatheringFailedError`; `errors.py:8` subclasses `ProviderError` (not a bare `Exception`); covered by `test_generate_judgment_raises_when_all_sources_fail` |
| `all_failed` semantics | Empty `call_plan` → no successful tool records → `any(...)` false (`phases.py:98,170–176`); fail-path test is consistent with production definition |
| Happy-path `call_plan=({},)` | Not a false pass: tools default missing keys to `[]` (`tools.py:91,117`), so empty-arg invokes succeed for ledger/wider telemetry |
| `session_trace_hash` stamp | `provider.py:131–136` `model_copy(..., session_trace_hash=registry.session_trace_hash())`; registry delegates to `compute_session_trace_hash` (`registry.py:128–129`) |
| Independent `lead_budget` | Separate dataclass fields + defaults (`provider.py:41–42,68–69`); Phase 1 gets `self.source_budget`, Phase 3 gets `self.lead_budget` only; no leftover arithmetic |
| Contract field | `contracts/judgment.py:28–31` optional `session_trace_hash: str \| None = None` |
| Orchestrator / engine | `rg agentic\|Agentic` under `src/praetor/engine` → **no matches**; orchestrator still maps only malformed/timeout/refusal/unavailable (`orchestrator.py:379–410`) — `AgenticEvidenceGatheringFailedError` **not** mapped |
| Policy | `rg agentic\|Agentic\|session_trace` under `src/praetor/policy` → **no matches** |
| Task 13 file delta on contract | `git diff HEAD -- src/praetor/contracts/judgment.py` is only the `session_trace_hash` field addition |

### Attempted refutations that failed

1. **Happy path should all-fail with `call_plan=({},)`** — Refuted by tool defaulting: missing `target_ids` / `evidence_ids` become `[]`, which is a successful invoke. E2E returns a real judgment.
2. **Dirty `src/praetor/policy` / `src/praetor/engine` in worktree ⇒ Task 13 changed them** — Worktree has prior-task dirt vs HEAD, but no agentic wiring and no Task-13-related symbols in those trees; claim is task-scope isolation, not a clean worktree.

## Gaps (non-refuting)

1. **Hash provenance under-tested** — e2e asserts `session_trace_hash is not None` and `len == 64` only; does not assert equality with `registry.session_trace_hash()`. Code path is direct and clear; gap is test strength, not implementation.
2. **Budget independence unexercised** — no test exhausts `source_budget` then asserts Phase 3 still receives a full independent `lead_budget`. Structural separation is visible in code; behavioral regression would not be caught.
3. **Phase ordering not spied** — tests rely on end-to-end Fake composition rather than call-order spies; ordering is evident from linear `provider.py` body.
4. **Worktree dirt outside allowed files** — engine/policy (and many other paths) remain modified from earlier agentic-judgment tasks; Task 13 deliverables align with allowed files, but a clean task-base diff was not available to prove exclusivity by git range alone.
5. **`__init__.py` encoding** — package docstring shows a mojibake em-dash in console (`�?"`); cosmetic only.

## Strongest reason

Fresh pytest/ruff/mypy all pass, and independent reads confirm the acceptance checklist behaviors in `provider.py` / contract / error hierarchy, with orchestrator and policy free of agentic wiring — attempted false-pass and scope-creep refutations did not hold.
