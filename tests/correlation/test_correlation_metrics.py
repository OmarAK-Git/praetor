"""Coverage for the correlation-layer unsupported-EventID metric (RFC-004)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.correlation import correlate_telemetry
from praetor.metrics.collector import MetricsCollector

ANCHOR = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)


def _sysmon_process_create(record_id: int) -> dict[str, object]:
    return {
        "record_id": str(record_id),
        "@timestamp": ANCHOR.isoformat().replace("+00:00", "Z"),
        "EventID": 1,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": "HOST-1",
        "EventData": {
            "Image": r"C:\Windows\System32\cmd.exe",
            "CommandLine": "cmd.exe /c whoami",
        },
    }


def _sysmon_unsupported(record_id: int) -> dict[str, object]:
    event = _sysmon_process_create(record_id)
    event["EventID"] = 99  # not in SUPPORTED_SYSMON_EVENT_IDS
    return event


def test_correlate_telemetry_records_metric_for_unsupported_sysmon_event_id() -> None:
    metrics = MetricsCollector()

    result = correlate_telemetry(
        sysmon_events=[_sysmon_process_create(1), _sysmon_unsupported(2)],
        security_events=[],
        anchor_time=ANCHOR,
        metrics=metrics,
    )

    assert len(result.bundle.facts) == 1
    assert metrics.snapshot().correlation_unsupported_event_id_total == 1


def test_correlate_telemetry_without_metrics_collector_does_not_raise() -> None:
    result = correlate_telemetry(
        sysmon_events=[_sysmon_unsupported(1)],
        security_events=[],
        anchor_time=ANCHOR,
    )

    assert result.bundle.facts == []
