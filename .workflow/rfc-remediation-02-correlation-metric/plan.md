# RFC Remediation 02 — Unsupported EventID Metric

Goal: Add and production-wire a metric that counts telemetry skipped because its EventID is unsupported.

Scope: RFC-004 metric field, collector, correlator wiring, orchestrator wiring, and focused tests only. Preserve correlation outputs and disposition behavior.

Allowed files:
- `src/praetor/metrics/events.py`
- `src/praetor/metrics/collector.py`
- `src/praetor/correlation/__init__.py`
- `src/praetor/engine/orchestrator.py`
- `tests/metrics/test_metrics.py`
- `tests/correlation/test_correlation_metrics.py`

Acceptance criteria:
1. `MetricsSnapshot.correlation_unsupported_event_id_total` exists.
2. Unsupported Sysmon and Security EventIDs increment it when a collector is supplied.
3. Production intake passes its collector to correlation.
4. Existing callers without metrics remain compatible.

Verification:
- `pytest tests/metrics/test_metrics.py tests/correlation/test_correlation_metrics.py tests/engine/ -v`
- `ruff check .`
- `mypy .`

Source plan: `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md`, Task 2.

Research decision: no researcher dispatch; the approved interfaces and production call chain are fully prescribed.
