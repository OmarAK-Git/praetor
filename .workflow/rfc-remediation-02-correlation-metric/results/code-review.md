# Code Review — rfc-remediation-02-correlation-metric

**Verdict: PASS**

**Commits reviewed:**
- `7d887027dc4a12ef06057a631a6dc96eeff776c4` — feature implementation
- `49df14be7ef114cfbf96d9a02b97238b78309455` — AC2 Security-branch test fix

**Scope:** RFC-004 correlation unsupported-EventID metric — field, collector, correlator + orchestrator wiring, focused tests  
**Plan:** `.workflow/rfc-remediation-02-correlation-metric/plan.md`  
**Source:** `docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` Task 2  
**Implementer result:** `.workflow/rfc-remediation-02-correlation-metric/results/implementer-result.md` (`DONE`, with review-fix section for `49df14b`)

## Summary

Feature commit `7d88702` implements the approved Task 2 surface correctly. Re-review of fix commit `49df14b` confirms the prior Important AC2 gap is closed: unsupported Security EventIDs are now exercised alongside Sysmon. No product-code changes in the fix; test-only, in allowed scope. Final verdict is PASS.

## Spec compliance

| Acceptance criterion | Result |
|---|---|
| `MetricsSnapshot.correlation_unsupported_event_id_total` exists | Met — field on dataclass; `MetricsCollector.snapshot()` passes it |
| Unsupported Sysmon and Security EventIDs increment when collector supplied | Met — both skip loops record; both families asserted in tests after `49df14b` |
| Production intake passes its collector to correlation | Met in code — `process_alert_intake` → `_resolve_intake_evidence_bundle(..., metrics_collector=...)` → `correlate_telemetry(..., metrics=metrics_collector)` |
| Existing callers without metrics remain compatible | Met — `metrics` / `metrics_collector` default `None`; no-collector correlation test covers the correlator path |

**Allowed files only:** `7d88702` touches the six planned paths; `49df14b` touches only `tests/correlation/test_correlation_metrics.py`. No unrelated product edits.

**Preserved semantics:** unsupported events still `continue` without changing filter/sort/bundle construction; dispositions and PolicyGate untouched; no Outcome Matrix fault flag; collector remains unlocked single-writer.

**Expected adaptation (not a defect):** source-plan nested `System.EventRecordID` / `EventData.UtcTime` fixtures adjusted to top-level `record_id` / `@timestamp` / `Computer` to match `event_field` and existing correlation fixtures.

## Re-review of prior blocker (`49df14b`)

Previous Important finding: Security unsupported-EventID metric branch untested.

Fix adds:

- Helpers `_security_successful_logon` (EventID `4624`) and `_security_unsupported` (EventID `4625`, outside `SUPPORTED_SECURITY_EVENT_IDS`)
- `test_correlate_telemetry_records_metric_for_unsupported_security_event_id` — mixed supported + unsupported Security events → `len(facts) == 1` and `correlation_unsupported_event_id_total == 1`

Deleting the Security `metrics.record_correlation_unsupported_event_id()` arm would now fail this test. AC2 coverage is adequate. Implementer reports `3 passed` for the correlation metrics file plus ruff/mypy clean.

## Production orchestrator wiring

Inspected `7d88702` vs plan Step 9:

- `_resolve_intake_evidence_bundle` gains defaulted `metrics_collector: MetricsCollector | None = None` and forwards `metrics=metrics_collector` into `correlate_telemetry`.
- Sole intake call site in `process_alert_intake` passes the existing intake `metrics_collector` through.
- Metric recording still occurs before the empty-facts → `correlation_failed` return, so schema-mismatch empty bundles are distinguishable from genuinely empty telemetry (the RFC-004 purpose).

## Snapshot constructor completeness

- `MetricsSnapshot` gains `correlation_unsupported_event_id_total: int` after `revocation_feed_unhealthy_transitions`.
- `MetricsCollector.__init__` initializes `_correlation_unsupported_event_id_total = 0`.
- `snapshot()` is the only `MetricsSnapshot(...)` construction site in the repo; it includes the new kwarg.
- No incomplete constructors or default-field holes.

## Sysmon and Security unsupported-EventID branches

Both families are wired symmetrically in `correlate_telemetry` (`supports_*` are EventID-set checks only). Both branches are now covered by dedicated tests.

## Correctness / security / simplicity

No Critical or Important defects. Observability-only counter; no new trust boundaries. Additive surface matches the plan; no speculative abstractions.

## Tests

| Coverage | Status |
|---|---|
| Collector increments → snapshot field | Present |
| Unsupported Sysmon EventID via `correlate_telemetry` | Present |
| Unsupported Security EventID via `correlate_telemetry` | Present (`49df14b`) |
| No-collector correlator compatibility | Present |
| Intake/`_resolve_intake_evidence_bundle` threads collector | Absent as a dedicated assertion; wiring verified by inspection + engine regression (plan Step 10) |

## Findings

### Critical

None.

### Important (blocking)

None — prior AC2 Security coverage finding resolved by `49df14b`.

### Minor (non-blocking)

1. **Production intake metric threading** — AC3 is correctly implemented in `orchestrator.py` but has no assertion that would fail if `metrics=metrics_collector` were dropped from the correlate call. Acceptable given source-plan Step 10 (engine suite regression); optional follow-up if stronger AC3 lock-in is desired.
2. **Source-plan vs fixture shape** — Fixture adaptation was necessary and correct; no product defect.

## Unrelated changes

None in `7d88702` or `49df14b`.

## Checked (audit trail)

- Full patch of `7d88702` (6 files, +88) and `49df14b` (1 test file, +40)
- Plan AC1–AC4 and source Task 2 Steps 1–11
- Updated implementer result review-fix section
- `SUPPORTED_SECURITY_EVENT_IDS` = `{4624}`; fixture uses `4625` as unsupported
- Security mixed supported/unsupported assertions vs “tests could pass without behavior”
- Orchestrator wiring and snapshot constructor completeness (unchanged from first review)
- Commit file sets vs allowed-files boundary
