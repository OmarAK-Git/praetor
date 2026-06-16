# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001 | Benchmark targets | `pytest -q tests/benchmarks/test_serialized_path.py` | pass | **7 passed** | pass |
| VERIFY-002 | REQ-002 | DEC-053 path fidelity | `test_production_path_transaction_structure`, `test_benchmark_iteration_write_set_uncontended` | pass | pass | pass |
| VERIFY-003 | REQ-003 | Runbook transaction count | `test_operator_runbook_transaction_count_matches_benchmark` | pass | pass | pass |
| VERIFY-004 | REQ-004 | Schema refs + disposition | `pytest -q tests/docs/test_docs.py` | pass | **10 passed** | pass |
| VERIFY-005 | REQ-005 | Runbook topics | `test_operator_runbook_required_topics` | pass | pass | pass |
| VERIFY-006 | REQ-006 | Doc test suite | `pytest -q tests/docs/` | pass | **10 passed** | pass |
| VERIFY-007 | — | Full suite | `pytest -q` | pass | **777 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-008 | — | Mypy | `mypy src evals consumer_sdk` | clean | **117 files** | pass |
| VERIFY-009 | — | Ruff | `ruff check src tests evals consumer_sdk benchmarks` | clean | clean | pass |

## Recorded sample run (2026-06-16, gatekeeper)

Hardware: developer workstation (Windows, local SQLite temp DB, activated `configs/example_org.yaml`).

```
operations=30
elapsed_seconds=0.147
sustained_alerts_per_minute=12210.8
target_sustained=30
target_burst=60
meets_sustained_target=True
burst_separately_measured=False
meets_burst_target_informational=True
```

Command: `run_serialized_path_benchmark(db, operations=30)` after `activate_org_config(EXAMPLE_CONFIG)`.

Interpretation: uncontended distinct-host DEC-053 path; not a production SLA. Revocation throughput remains `benchmarks/smoke_serialized_path.py`.

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live Splunk saved-search validation | Manual procedure only per `splunk/README.md`; `test_splunk_demo_manual_procedure_only` checks prerequisites only | Phase 5 Splunk demo is operator-executed, not CI-gated |
