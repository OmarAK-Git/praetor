# Final Report: TASK-035 (gatekeeper realignment)

## Summary

Gatekeeper pass realigned the production throughput benchmark to mirror DEC-053 production intake after terminal stamp, corrected operator documentation and tests, and recorded a sample measured run.

## Key change (DEC-056)

**Before:** `persist_directive=True` in gate, separate ledger tx, spurious `NEVER_CONTAIN_CONFLICT` revocation per iteration.

**After:** `evaluate_policy_gate(..., persist_directive=False)` → one engine `critical_transaction` with `persist_deferred_policy_gate_directive_in_transaction` + ledger append. No per-alert revocation (smoke benchmark remains separate).

## Files changed (gatekeeper)

- `benchmarks/serialized_path.py` — DEC-053 faithful path, `benchmark_result_from_timing`, contended pair helper
- `tests/benchmarks/test_serialized_path.py` — **7** tests (transaction structure, write-set, semantics, contended, sample run)
- `tests/docs/test_docs.py` — transaction-count doc test
- `docs/operator_runbook.md`, `docs/architecture.md`, `docs/contracts.md`, `docs/eval_gates.md`
- `docs/decisions.md` — DEC-056
- `tests/splunk/test_savedsearch_generation.py` — manual-only test rename
- `memory-bank/decisions.md` — DEC-056

## Verification

```
pytest -q tests/benchmarks/test_serialized_path.py — 7 passed
pytest -q tests/docs/test_docs.py — 10 passed
pytest -q — 777 passed, 2 deselected, 1 xfailed
mypy src evals consumer_sdk — 117 files clean
ruff check … — clean
```

Sample run (30 ops): **12210.8** alerts/min sustained vs target **30** (`meets_sustained_target=True`). See `.workflow/TASK-035/verification.md`.

## Known gaps

- Burst rate not measured in separate window in v1.
- Splunk demo remains manual-only (no automated saved-search CI gate).
- Benchmark sample is developer-hardware specific.

## safe_to_commit

yes — 2026-06-16 gatekeeper verification green
