# Fresh-Context Verification Packet

Queue item: `rfc-remediation-02-correlation-metric`

Goal: Add and production-wire a metric that counts telemetry skipped because its EventID is unsupported.

Acceptance criteria:
1. `MetricsSnapshot.correlation_unsupported_event_id_total` exists.
2. Unsupported Sysmon and Security EventIDs increment it when a collector is supplied.
3. Production intake passes its collector to correlation.
4. Existing callers without metrics remain compatible.

Changed paths are the six allowed paths in `plan.md`.
Implementation result: `.workflow/rfc-remediation-02-correlation-metric/results/implementer-result.md`
Code review: `.workflow/rfc-remediation-02-correlation-metric/results/code-review.md`
Commits: `7d88702`, `49df14b`

Commands:
- `pytest tests/metrics/test_metrics.py tests/correlation/test_correlation_metrics.py tests/engine/ -v`
- `ruff check .`
- `mypy .`

Treat prior claims as unevidenced. Independently inspect production wiring and both telemetry branches. Verify task scope only. Remain read-only except for the verifier result artifact.
