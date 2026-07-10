# Implementer Result — V2-020 Metrics Production Completeness

## Status

Complete — verification green. Queue item **not** marked done (per packet).

## Files Changed

| File | Rationale |
|------|-----------|
| `src/praetor/metrics/events.py` | Added `is_llm_failure_fault_flag()` helper for production wiring guard |
| `src/praetor/metrics/__init__.py` | Exported `is_llm_failure_fault_flag` |
| `src/praetor/engine/orchestrator.py` | `_record_intake_metrics_bypass_gate` only calls `record_llm_failure` for `LLM_FAILURE_FAULT_FLAGS` |
| `src/praetor/revocation/exporter.py` | Records `record_feed_export_lag` on verified export completion; optional `metrics` param threaded through export hooks |
| `evals/harness.py` | Optional `metrics` expectations for `engine_intake`; passes `MetricsCollector` to intake |
| `evals/scenarios/provider_unavailable.yaml` | Pins LLM-failure and gate-evaluation metrics |
| `evals/scenarios/correlation_failure.yaml` | Pins empty `llm_failure_by_fault_flag` (non-LLM fault) |
| `docs/operator_runbook.md` | Documents export-completion lag recording and single-writer thread-safety assumption |
| `tests/metrics/test_orchestrator_metrics.py` | Correlation failure no longer expects LLM failure counter |
| `tests/metrics/test_metrics_completeness.py` | Feed lag on export, LLM-flag guard, thread-safety documentation/concurrency tests |
| `tests/evals/test_metrics_expectations.py` | Harness metrics expectation integration tests |
| `.workflow/v2-020-metrics-completeness/plan.md` | Task plan |
| `.workflow/v2-020-metrics-completeness/packets/implementer.md` | Implementer packet |

## Behavior Summary

1. **Feed export lag** — `export_next_pending_row` / `export_pending_feed_rows` / startup hooks accept optional `metrics: MetricsCollector`. After `mark_feed_row_exported` (normal write or crash recovery), lag is computed from `ledger_commit_at` to export completion time. Intake does not record feed lag.

2. **LLM failure guard** — Production intake bypass-gate path records disposition for all system faults but increments `llm_failure_by_fault_flag` only when the fault is in `LLM_FAILURE_FAULT_FLAGS` (provider/model-quality flags). Policy/system faults like `correlation_failure` and `config_over_budget` no longer pollute LLM failure metrics.

3. **Thread safety** — `MetricsCollector` retains v1 single-writer docstring; runbook documents the assumption; concurrency test documents undefined-but-non-crashing behavior under parallel writers.

4. **Harness** — `engine_intake` scenarios may include optional `expectations.metrics` dict compared against `metrics.snapshot()` fields.

## Verification

```bash
pytest tests/metrics/ tests/evals/ -q
```

```
133 passed, 1 deselected in 16.02s
```

## Unresolved / Out of Scope

- Runtime startup (`open_production_state_store`) does not yet pass a shared `MetricsCollector` into `run_feed_startup_hook_for_db`; export functions accept optional metrics for callers that wire it.
- Queue status unchanged (`in_progress`); verifier pass pending.

## Approval Gates

None required for this implementer pass.
