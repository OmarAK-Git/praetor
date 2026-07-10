# Workflow Plan — V2-020 Metrics Production Completeness

## Goal

V2-020 — Metrics production completeness: feed export lag on completion; `record_llm_failure` uses only `LLM_FAILURE_FAULT_FLAGS`; metrics thread-safety documented or guarded.

## Scope

Metrics wiring and production call sites only. Do not run V2 Gate 3 exit.

## Tier

T2

## Acceptance Criteria

1. Feed export lag is recorded on export completion, not guessed at intake.
2. `record_llm_failure` production call sites pass only `LLM_FAILURE_FAULT_FLAGS`.
3. `MetricsCollector` thread-safety is documented as single-writer or guarded with locking and a concurrency test.
4. `engine_intake` eval optionally asserts rate-counter side effects.
5. Verifier checks only V2-020 acceptance, not V2 Gate 3 completion.

## Implementation Steps

1. Wire `record_feed_export_lag` in `revocation/exporter.py` after verified export completion.
2. Guard `_record_intake_metrics_bypass_gate` so only `LLM_FAILURE_FAULT_FLAGS` reach `record_llm_failure`.
3. Document single-writer assumption in runbook; add documentation/concurrency assertion test.
4. Add optional `metrics` expectations to `engine_intake` harness runner and scenario pins.
5. Add tests in `tests/metrics/` and `tests/evals/`.

## Verification Commands

```bash
pytest tests/metrics/ tests/evals/ -q
```
