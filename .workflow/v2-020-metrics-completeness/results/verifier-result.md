# Verifier Result — V2-020 Metrics Production Completeness

## Verdict

**survives** (accept) — all five V2-020 acceptance criteria are backed by real behavior and passing tests. One disclosed residual gap (runtime startup wiring) is confirmed out of scope for this task.

## Method

Adversarial verification: re-ran the verification command myself, read the actual production code (not the implementer transcript), traced every production call site, and checked each acceptance criterion for gaming (weakened assertions, source-only tests, intake-vs-completion confusion, alternate call sites).

## Verification Command (re-run by verifier)

```bash
python -m pytest tests/metrics/ tests/evals/ -q
# 133 passed, 1 deselected in 13.87s  (exit 0)
```

Matches the implementer's claimed `133 passed, 1 deselected`.

## Criterion-by-Criterion Evidence

### AC1 — Feed export lag recorded on export completion, not intake — PASS
- `record_feed_export_lag` (production) is reachable **only** via `_record_feed_export_lag_on_completion` (`src/praetor/revocation/exporter.py:115`), which is called **after** `mark_feed_row_exported` at `exporter.py:271` (crash-recovery path) and `exporter.py:380` (normal write path). Grep confirms no other production caller and no intake-side call.
- Lag is computed from `fetch_ledger_commit_at(...)` to `export_completed_at`, not guessed at intake (`exporter.py:126-133`).
- Behavioral test `test_feed_export_records_lag_on_completion` (`tests/metrics/test_metrics_completeness.py:46`) proves a 25.0s sample from ledger commit → export completion, with the 60s warning threshold recorded. Not a weakened/source-only test.

### AC2 — `record_llm_failure` production sites pass only `LLM_FAILURE_FAULT_FLAGS` — PASS
- Single guarded chokepoint: all four intake call sites (`orchestrator.py:592,636,720,768`) route through `_record_intake_metrics_bypass_gate`, which gates on `is_llm_failure_fault_flag(fault_flag)` before `metrics.record_llm_failure(...)` (`orchestrator.py:157-158`).
- Grep confirms `record_llm_failure` has no other production caller (only the collector definition + tests).
- Behavioral tests back this: `test_bypass_gate_skips_non_llm_fault_flags` (correlation_failure → no counter) and `test_bypass_gate_records_llm_failure_for_provider_flags` (provider_unavailable → counter=1). The source-inspection test at line 70 is weak on its own but is corroborated by these behavioral tests.

### AC3 — Thread-safety documented (single-writer) or guarded + concurrency test — PASS
- Documented both in code (`collector.py:32`: "Thread-unsafe in-process collector; v1 single-writer process assumption") and in `docs/operator_runbook.md:149-151`.
- Concurrency test present (`test_metrics_collector_concurrent_writes_are_undefined_but_do_not_crash`). Minor quibble: the test asserts an exact count of 200 under 4 threads while framing behavior as "undefined" (passes in practice under the CPython GIL) — but the criterion is satisfied by the single-writer documentation regardless, so this does not affect the verdict.

### AC4 — `engine_intake` eval optionally asserts rate-counter side effects — PASS
- Harness threads a real `MetricsCollector` into intake (`evals/harness.py:742`) and compares `metrics.snapshot()` fields against an optional `expectations.metrics` mapping via `_assert_metrics_expectations` (`harness.py:664-675`, invoked at `harness.py:813`). It is genuinely optional (returns early when absent).
- Scenarios pin real counters: `provider_unavailable.yaml` asserts `llm_failure_by_fault_flag.provider_unavailable == 1` and `policy_gate_evaluations_total == 0`; `correlation_failure.yaml` asserts `llm_failure_by_fault_flag == {}`.
- Integration tests `test_provider_unavailable_scenario_asserts_llm_failure_metrics` and `test_correlation_failure_scenario_asserts_no_llm_failure_metrics` run the scenarios and assert `result.passed`, so the harness truly enforces the pins (not a no-op).

### AC5 — Verifier scope limited to V2-020 — COMPLIED
- This verification checked only the four substantive V2-020 criteria. No V2 Gate 3 exit checks were performed.

## Adjudication of Implementer's Open Question (runtime wiring)

The implementer flagged that `open_production_state_store` does not pass a shared `MetricsCollector` into feed export.

Confirmed: `src/praetor/runtime/startup.py` neither constructs a `MetricsCollector` nor invokes any feed startup hook — there is no production feed-export loop here to wire metrics into. This is **out of scope** for V2-020 because:
1. AC1 as written requires the lag to be recorded *on export completion* (a mechanism), which exists and is tested — it does not require a live runtime collector singleton.
2. `src/praetor/runtime/startup.py` is **not** in the implementer packet's Allowed Files, and the packet explicitly says to stop before writes outside allowed files.

## Residual Gap (disclosed, non-blocking for V2-020)

In the live runtime, `feed_export_lag` samples will not populate until a future task constructs a metrics singleton and threads it into the production feed-export path. The export functions already accept an optional `metrics=` param, so this is a wiring follow-up (candidate for the runtime/observability task feeding V2 Gate 3), not a defect in V2-020.

## Bottom Line

Claim of completion **survives** adversarial verification. All acceptance criteria are supported by fresh, behavioral evidence; the only limitation is a correctly-disclosed, out-of-scope runtime wiring follow-up.
