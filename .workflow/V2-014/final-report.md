# Final Report — V2-014

## Summary

Implemented **correlator host isolation (Gate 2)**: `correlate_telemetry` scopes in-window events to the anchor host before normalization, dropping cross-host noise (record 1004 / WORKSTATION2) while retaining same-host incidental noise (1003). REVIEW-004 strict xfail removed.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 Anchor-host filtering | `host_isolation.py`, `correlate_telemetry` wiring |
| REQ-002 1004 excluded, 1003 retained | `test_correlator_should_drop_cross_host_in_window_noise`, `test_host_isolation.py` |
| REQ-003 Out-of-window unchanged | `test_window_excludes_out_of_window_record_9999` |
| REQ-004 Citation targeting | `test_citation_anchored_host_targeting.py` (5 passed) |
| REQ-005 Gates green | VERIFY-001–007 |

## Files changed

**Production**
- `src/praetor/correlation/host_isolation.py` (new)
- `src/praetor/correlation/__init__.py`

**Tests / evals**
- `tests/correlation/test_host_isolation.py` (new)
- `tests/evals/test_phase3_regression_gate.py`
- `tests/evals/test_correlation_gate.py`
- `evals/correlation_expected/noisy_correlated_real_telemetry.yaml`
- `evals/correlation_expected/otrf_unrelated_in_window_noise.yaml`

**Workflow**
- `.workflow/V2-014/*`

## Verification (2026-06-30)

```
python -m pytest -q tests/correlation/test_host_isolation.py tests/evals/test_correlation_gate.py tests/evals/test_phase3_regression_gate.py tests/policy/test_citation_anchored_host_targeting.py → 44 passed
python -m pytest -q                    → 842 passed, 2 deselected
python -m mypy src evals consumer_sdk  → 119 files clean
python -m ruff check src tests evals consumer_sdk → clean
python -m evals.run_phase3_gate --skip-harness --skip-identity-subprocess → all PASS
python -m evals.harness                → 31/31 PASS
```

## Known gaps

- Playbook AG-0080 digest entry stale until dream consolidate.
- Orchestrator does not yet pass explicit `anchor_host_id` from alert context (V2-015).

## safe_to_commit

yes — verification green
