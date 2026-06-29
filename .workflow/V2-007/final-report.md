# Final Report — V2-007

## Summary

Completed **ProviderUnavailable intake handling (V2-007)**: intake maps `ProviderUnavailableError` to the DEC-061 Outcome Matrix row; provider-health breaker records production failures on all typed provider-fault intake exits; metrics record `provider_unavailable` under approved `LLM_FAILURE_FAULT_FLAGS`.

## Worktree

- Branch: `task/V2-007`
- Path: `C:\Users\oalan\Praetor\.worktrees\V2-007`
- Base: `d352e45` (V2-005)

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 Intake catch | `orchestrator.py` + `test_provider_unavailable_intake_escalates` |
| REQ-002 Outcome Matrix edict | `assert_outcome_matrix_edict` SFE=true |
| REQ-003 Breaker recording | `_record_provider_breaker_failure_hook` + `test_provider_unavailable_records_breaker_production_failure` |
| REQ-004 Metrics LLM flags | `test_intake_records_provider_unavailable_llm_failure_metric` |

## Files changed

**Production**
- `src/praetor/engine/orchestrator.py` — breaker hook on provider faults; provider-health metrics gauge
- `src/praetor/engine/edict.py` — optional `in_transaction_hook` on persist

**Tests**
- `tests/engine/test_provider_unavailable_intake.py` (new)
- `tests/metrics/test_orchestrator_metrics.py` — provider unavailable metrics test

**Workflow / memory bank**
- `.workflow/V2-007/*`, `memory-bank/{tasks,activeContext,progress}.md`

## Verification

Scoped (2026-06-29):

```
python -m pytest tests/engine/ tests/metrics/ tests/judgment/test_provider_failures.py tests/judgment/test_provider_health_breaker.py tests/evals/test_provider_unavailable_matrix.py tests/evals/test_eval_harness.py -q
python -m mypy src evals consumer_sdk
python -m ruff check src tests evals consumer_sdk
python -m evals.harness --scenario provider_unavailable
```

| Check | Result |
|---|---|
| Scoped pytest | **161 passed** |
| mypy | **118** files, no issues |
| ruff | clean (after import fix) |
| harness scenario | provider_unavailable PASS |

Full `pytest -q` on V2-005 base: **767 passed, 30 failed** (pre-existing; see review.md).

## Known gaps

- Production success metric on happy-path intake deferred.
- Full-suite green depends on merging/rebasing V2-006+ policy test fixes.

## safe_to_commit

yes — V2-007 scoped verification green (2026-06-29)
