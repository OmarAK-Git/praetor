# Implementer result — agentic-judgment-13-provider

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/contracts/judgment.py` | Added optional `ModelJudgment.session_trace_hash` (DEC-064; backward compatible). |
| `src/praetor/judgment/agentic/provider.py` | New `AgenticJudgmentProvider` composing Phase 1 fan-out, Phase 2 debate, Phase 3 reconciliation. |
| `src/praetor/judgment/agentic/__init__.py` | Re-export `AgenticJudgmentProvider`. |
| `tests/judgment/agentic/test_provider.py` | TDD end-to-end provider tests with Fake models. |

## Implementation summary

- **`AgenticJudgmentProvider`** implements `JudgmentProvider.generate_judgment` and `probe`.
- Requires `request.evidence_bundle` — raises `ProviderUnavailableError` when missing.
- Resolves org-config snapshot via `fetch_snapshot_by_hash`; raises `ProviderUnavailableError` when absent.
- Phase 1: `run_source_fanout` with `source_budget` (default 5 calls / 20s).
- Phase 2: `run_hypothesis_debate` (reasoning-only over registry).
- Phase 3: `run_lead_reconciliation` with independent `lead_budget` (default 0 calls / 15s) — never derived from Phase 1/2 leftovers.
- Raises `AgenticEvidenceGatheringFailedError` when `fanout_result.all_failed`.
- Returns `ModelJudgment` with `session_trace_hash` from `registry.session_trace_hash()`, plus provider metadata.

## Verification commands and outcomes

```
PYTHONPATH=... pytest tests/judgment/agentic tests/evidence/test_provenance.py tests/hashing/test_domains.py tests/ledger/test_target_history.py -q
→ 44 passed in 1.60s

PYTHONPATH=... ruff check src/praetor/contracts/judgment.py src/praetor/judgment/agentic tests/judgment/agentic
→ All checks passed!

cd .worktrees/agentic-judgment && PYTHONPATH=... mypy src/praetor/contracts/judgment.py src/praetor/judgment/agentic
→ Success: no issues found in 10 source files
```

### TDD evidence

1. Tests written first → `ModuleNotFoundError: No module named 'praetor.judgment.agentic.provider'` (expected).
2. Implementation added → 4/4 provider tests pass; full agentic + related suite 44/44.

## Gaps / deviations from plan test scaffold

1. **Org-config snapshot binding** — Plan used placeholder hash `"h"`; tests persist a real snapshot via `_bind_org_config()` and use its `snapshot_hash` so `fetch_snapshot_by_hash` succeeds in end-to-end paths.
2. **Thread-safe SQLite for integration tests** — Phase 1 fan-out uses `ThreadPoolExecutor`; tests reopen the DB with `check_same_thread=False` via `_open_thread_safe_store()` (production connection policy unchanged; outside Task 13 write scope).
3. **Outcome Matrix / orchestrator wiring** — Not touched (Task 14).
4. **No commit** (per standing orders).
5. **Queue item not marked done** (per standing orders).
