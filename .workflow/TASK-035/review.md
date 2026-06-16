# Review: TASK-035 (gatekeeper realignment)

## Summary

Realigned production benchmark to DEC-053 (gate `persist_directive=False` + single engine commit); removed spurious per-alert revocation; corrected runbook transaction claims; pinned comparison semantics and contended-path coverage; downgraded Splunk to manual-only CI posture.

## Findings addressed

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| REVIEW-001 | high | Benchmark used `persist_directive=True` + second tx + per-alert revocation | DEC-056: faithful DEC-053 path; smoke benchmark for revocation |
| REVIEW-002 | high | Runbook claimed one transaction per iteration | Corrected to two; doc test pins constant |
| REVIEW-003 | medium | Burst silently aliased to sustained | `burst_separately_measured=False`; informational burst compare only |
| REVIEW-004 | medium | No contended-path measurement | `run_contended_production_path_pair` + test; runbook documents uncontended best case |
| REVIEW-005 | medium | Splunk test always skipped | Renamed manual-only; eval_gates/runbook wording updated |
| REVIEW-006 | low | Target comparison untested | `test_benchmark_target_comparison_semantics` + recorded sample run |

## safe_to_commit

yes — verification green 2026-06-16 (gatekeeper)
