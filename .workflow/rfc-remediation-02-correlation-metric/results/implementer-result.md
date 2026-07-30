# Implementer Result — rfc-remediation-02-correlation-metric

## Status

DONE

## Model

composer-2.5

## Changed files

| File | Rationale |
|------|-----------|
| `src/praetor/metrics/events.py` | Added `correlation_unsupported_event_id_total` field to `MetricsSnapshot`. |
| `src/praetor/metrics/collector.py` | Added counter, `record_correlation_unsupported_event_id()`, and snapshot wiring. |
| `src/praetor/correlation/__init__.py` | Threaded optional `metrics` param through `correlate_telemetry`; increments on unsupported Sysmon/Security EventIDs. |
| `src/praetor/engine/orchestrator.py` | Passed `metrics_collector` from intake into `_resolve_intake_evidence_bundle` → `correlate_telemetry`. |
| `tests/metrics/test_metrics.py` | Added collector/snapshot increment test for the new metric. |
| `tests/correlation/test_correlation_metrics.py` | New wiring tests for metric recording and backward-compatible no-collector path. |

## Red / green evidence

**Red — metrics layer** (`pytest tests/metrics/test_metrics.py::test_record_correlation_unsupported_event_id_increments_snapshot -v` before implementation):

```
AttributeError: 'MetricsCollector' object has no attribute 'record_correlation_unsupported_event_id'
```

**Green — metrics layer** (after implementation):

```
1 passed in 0.03s
```

**Red — correlation wiring** (`pytest tests/correlation/test_correlation_metrics.py -v` before `correlate_telemetry` change):

```
TypeError: correlate_telemetry() got an unexpected keyword argument 'metrics'
1 failed, 1 passed
```

**Green — correlation wiring** (after implementation, fixture adjusted to repo field style):

```
2 passed
```

## Verification outputs

### pytest

```
pytest tests/metrics/test_metrics.py tests/correlation/test_correlation_metrics.py tests/engine/ -v
97 passed in 8.30s
```

### ruff

```
All checks passed!
```

### mypy

```
Success: no issues found in 134 source files
```

## Commit

`7d88702`

Message: `correlation: add distinct metric for unsupported-EventID schema mismatches`

## Concerns

- Source plan fixture used nested `System.EventRecordID` and `EventData.UtcTime`; adjusted to top-level `record_id`, `@timestamp`, and `Computer` to match `event_field` extraction and existing correlation fixtures.

## Review fix (AC2 Security branch)

**Change:** Added `test_correlate_telemetry_records_metric_for_unsupported_security_event_id` with `_security_successful_logon` / `_security_unsupported` helpers shaped like `tests/fixtures/security/successful_logon_4624.json` (4624 supported, 4625 unsupported).

**Verification:**

```
pytest tests/correlation/test_correlation_metrics.py -v
3 passed in 0.03s
```

```
ruff check .
All checks passed!
```

```
mypy .
Success: no issues found in 134 source files
```

**Commit:** `49df14b` — `test: cover Security unsupported-EventID correlation metric branch`
