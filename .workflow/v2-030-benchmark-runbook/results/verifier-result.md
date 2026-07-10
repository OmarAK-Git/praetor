# Verifier Result — V2-030 Benchmark Burst Measurement and Runbook Pins

## Verdict

**survives** (task-scoped)

The implementer's completion claim ("verification green — `pytest tests/benchmarks/ tests/docs/ -q` → 25 passed") is reproduced and the tests genuinely exercise the claimed behavior. I could not refute it within the task scope.

## Claim Restated

1. `pytest tests/benchmarks/ tests/docs/ -q` passes with 25 tests.
2. Every `SerializedPathBenchmarkResult` carries a `BenchmarkMeasurementContext` (hardware/scenario metadata, `informational_only=True`).
3. Burst is honest in v1: `burst_separately_measured=False`, no separate burst window, `meets_burst_target_informational` reuses the sustained rate.
4. Runbook pins example-org targets (30/60), the two-transaction claim, the burst-honesty flag, and measurement-context wording.

## Evidence Gathered

### 1. Command reproduced (fresh run)

```
python -m pytest tests/benchmarks/ tests/docs/ -q
.........................                                                [100%]
25 passed in 1.75s   (exit code 0)
```

25 dots → 25 executed, 0 skipped, 0 xfailed. Matches the implementer's "25 passed".

### 2. Tests invoke real code, not gamed fixtures

- `tests/benchmarks/test_serialized_path.py:88` — `test_benchmark_result_always_emits_measurement_context` calls `run_serialized_path_for_store(...)`, which routes through `benchmark_result_from_timing` (`benchmarks/serialized_path.py:172-195`) and populates `measurement_context` via `collect_benchmark_measurement_context()` (`benchmarks/serialized_path.py:87-99`, real `platform`/`os.cpu_count()` reads). Not a stub.
- `tests/benchmarks/test_serialized_path.py:107` — `test_benchmark_burst_not_measured_in_separate_window` asserts `burst_separately_measured is False` **and** `not hasattr(result, "burst_alerts_per_minute")`. The negative-attribute assertion is a real refutation guard against a fabricated separate-burst field, backed by the frozen dataclass having no such field (`serialized_path.py:102-114`).
- `tests/benchmarks/test_serialized_path.py:140-231` — production-path tests use `patch.object(... "critical_transaction", counting_critical)` and assert exactly `PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION == 2` BEGIN IMMEDIATE txns, ledger `+2` rows, feed-outbox unchanged, and second-directive suppression at DB level. These exercise the real serialized path, not the timing helper.

### 3. Doc tests read real files (no hardcoded pass)

- `tests/docs/test_docs.py:61-75` loads `configs/example_org.yaml` at runtime, asserts `sustained==30`/`burst==60`, and requires those exact strings in `docs/operator_runbook.md`. Independent grep confirms the runbook text:
  - `docs/operator_runbook.md:58` — `burst_separately_measured=false` + "does **not** measure burst in a separate time window".
  - `docs/operator_runbook.md:60` — `measurement_context`, `uncontended_distinct_host`, `informational_only=true`, "not production SLAs".
- `tests/docs/test_docs.py:46-58` cross-checks the runbook's "**two** `BEGIN IMMEDIATE`" against the imported constant `PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION`, so doc and code cannot silently drift.

### 4. Scope check

All four files named in the implementer result are present as modified (`git status --porcelain`): `benchmarks/serialized_path.py`, `tests/benchmarks/test_serialized_path.py`, `docs/operator_runbook.md`, `tests/docs/test_docs.py`. The task-scoped command touches only `tests/benchmarks/` and `tests/docs/`; other working-tree changes belong to prior V2 tasks and are outside this task's verification scope.

## Attempts to Refute (all failed)

- **Weakened `burst_separately_measured` assertion?** Partly tautological (constant vs constant), but paired with `not hasattr(..., "burst_alerts_per_minute")` and the runbook honesty pins, the *intent* (v1 does not fabricate a separate burst measurement) is enforced. Not a hollow pass.
- **Skipped/deselected tests inflating "passed"?** No — 25 dots, no `s`/`x` markers, exit 0.
- **Stale evidence?** Re-ran the exact command against current working tree; result matches.
- **Doc test asserting a literal instead of the file?** No — it reads `operator_runbook.md` and `example_org.yaml` from disk at runtime.

## Residual Notes (not refutations)

- Out-of-scope items the implementer already disclosed remain true: `evals/run_phase5_benchmark.py` does not print `measurement_context`; separate burst-window measurement is deferred (GR-0010). These are honest deferrals, consistent with the honesty flags, and do not affect the task-scoped command.
- Queue item correctly left `in_progress` (not marked done) per packet.

## Bottom Line

`refuted`? No. **survives** — the task-scoped command passes on a fresh run and the assertions genuinely bind to the implemented behavior and the on-disk runbook/config.
