# Verifier Result — rfc-remediation-02-correlation-metric

**Outcome:** PASS  
**Verifier:** skeptic-verifier (fresh context; implementer/reviewer claims treated as unevidenced)  
**Commits checked:** `7d887027dc4a12ef06057a631a6dc96eeff776c4`, `49df14be7ef114cfbf96d9a02b97238b78309455` (both ancestors of `HEAD`=`49df14b`)  
**Scope:** task acceptance criteria only (plan allowed paths)

## Claim under test

Add and production-wire a metric that counts telemetry skipped because its EventID is unsupported: snapshot field, Sysmon+Security correlator increments when a collector is supplied, intake passes its collector into correlation, and callers without metrics remain compatible.

## Independent commands (reproduced)

| Command | Result |
|---------|--------|
| `pytest tests/metrics/test_metrics.py tests/correlation/test_correlation_metrics.py tests/engine/ -v` | **98 passed** in 8.44s (exit 0) |
| `ruff check .` | All checks passed! (exit 0) |
| `mypy .` | Success: no issues found in 134 source files (exit 0) |

Scoped product/test paths have no dirty diff vs the commits (`git status --short` empty for the six allowed files). Commit file sets stay inside the plan allow-list (`7d88702`: six paths; `49df14b`: `tests/correlation/test_correlation_metrics.py` only).

## Acceptance criteria

### AC1 — `MetricsSnapshot.correlation_unsupported_event_id_total` exists — PASS

- Field on `MetricsSnapshot` at `src/praetor/metrics/events.py:146`.
- Collector initializes `_correlation_unsupported_event_id_total = 0` (`collector.py:73`), exposes `record_correlation_unsupported_event_id()` (`collector.py:176-183`), and passes the counter into the sole `MetricsSnapshot(...)` construction site (`collector.py:224-226`).
- `test_record_correlation_unsupported_event_id_increments_snapshot` PASSED (asserts snapshot total `== 2` after two records).

### AC2 — Unsupported Sysmon and Security EventIDs increment when collector supplied — PASS

- Both skip loops in `correlate_telemetry` call `metrics.record_correlation_unsupported_event_id()` when `metrics is not None` (`correlation/__init__.py:76-87`).
- Runtime confirmation: `SUPPORTED_SYSMON_EVENT_IDS={1}`, `SUPPORTED_SECURITY_EVENT_IDS={4624}`; fixtures use EventID `99` / `4625` → `supports_*` returns `False`.
- Dedicated tests both PASSED:
  - `test_correlate_telemetry_records_metric_for_unsupported_sysmon_event_id` — mixed Sysmon → `facts==1`, metric `==1`
  - `test_correlate_telemetry_records_metric_for_unsupported_security_event_id` — mixed Security → `facts==1`, metric `==1`
- Deleting either recording arm would fail the corresponding family-specific assertion (not a single shared counter-only check).

### AC3 — Production intake passes its collector to correlation — PASS

- `_resolve_intake_evidence_bundle` accepts defaulted `metrics_collector` and forwards `metrics=metrics_collector` into `correlate_telemetry` (`orchestrator.py:113`, `123-127`).
- Sole production intake call site in `process_alert_intake` passes the intake `metrics_collector` through (`orchestrator.py:277-283`).
- Repo-wide `correlate_telemetry(` call sites: production wiring is only this orchestrator path; other callers are tests/evals (intentionally optional metrics).

### AC4 — Existing callers without metrics remain compatible — PASS

- `metrics: MetricsCollector | None = None` is keyword-only with default (`correlation/__init__.py:43`).
- Recording is gated by `if metrics is not None` on both branches.
- `test_correlate_telemetry_without_metrics_collector_does_not_raise` PASSED (unsupported Sysmon, no collector → empty facts, no exception).
- Engine suite regression PASSED (98 total including engine/), covering intake without requiring a collector.

## Attempts to refute (failed)

1. **Stale evidence / dirty tree** — both claimed commits are ancestors of `HEAD`; allowed paths clean vs working tree.
2. **Gamed EventIDs** — `supports_sysmon_event` / `supports_security_event` are EventID-set checks only; `99` and `4625` are outside the frozensets (confirmed via import).
3. **One family untested** — Security branch has a dedicated mixed-event metric assertion after `49df14b`; not Sysmon-only coverage.
4. **Snapshot constructor hole** — only one `MetricsSnapshot(` site in `src/`; includes the new field.
5. **Scope creep** — commit name-only lists match the six allowed paths (+ review-fix test-only path).
6. **AC3 untested → unmet** — absence of a dedicated intake metric-thread assertion is a coverage gap, not an implementation miss; wiring verified by direct read of the production call chain.

## Residual notes (non-blocking; do not change outcome)

- No test asserts that dropping `metrics=metrics_collector` from the orchestrator `correlate_telemetry` call would fail; AC3 rests on code inspection + engine regression (as planned).
- Other `correlate_telemetry` call sites (evals/tests) do not pass a collector; that matches AC4 optional wiring, not a production-intake defect.

## Verdict

**PASS** — all four acceptance criteria are backed by independently reproduced pytest/ruff/mypy evidence plus direct inspection of both correlator skip arms and the intake → `_resolve_intake_evidence_bundle` → `correlate_telemetry` metrics hand-off.
