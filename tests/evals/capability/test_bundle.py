from __future__ import annotations

from datetime import UTC, datetime

from evals.capability.bundle import build_spike_bundle

ANCHOR = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _event(
    *,
    record_id: str,
    event_id: int,
    host: str = "ws-01",
    utc: str = "2026-01-01 12:00:00.000",
    channel: str = "Microsoft-Windows-Sysmon/Operational",
) -> dict[str, object]:
    return {
        "EventID": event_id,
        "Channel": channel,
        "EventRecordID": record_id,
        "Computer": host,
        "UtcTime": utc,
        "EventData": {"Image": r"C:\Windows\System32\cmd.exe"},
    }


def test_includes_event_types_correlation_rejects() -> None:
    events = [
        _event(record_id="1", event_id=3),
        _event(record_id="2", event_id=11),
        _event(record_id="3", event_id=13),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR)
    assert len(bundle.facts) == 3


def test_events_outside_window_excluded() -> None:
    events = [
        _event(record_id="1", event_id=1),
        _event(record_id="2", event_id=1, utc="2026-01-01 13:00:00.000"),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR, window_seconds=300)
    assert len(bundle.facts) == 1
    assert bundle.facts[0].source_event_reference.endswith(":1:1")


def test_events_from_other_hosts_excluded() -> None:
    events = [
        _event(record_id="1", event_id=1, host="ws-01"),
        _event(record_id="2", event_id=1, host="ws-02"),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR, anchor_host_id="ws-01")
    assert len(bundle.facts) == 1
    assert bundle.facts[0].normalized_fields["host_id"] == "ws-01"


def test_provenance_paths_derived_per_source() -> None:
    events = [
        _event(record_id="1", event_id=3),
        _event(record_id="2", event_id=4624, channel="Security"),
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR)
    paths = {fact.provenance_path for fact in bundle.facts}
    assert paths == {"sysmon_event_log", "windows_security_log"}


def test_empty_input_produces_empty_bundle() -> None:
    bundle = build_spike_bundle([], anchor_time=ANCHOR)
    assert bundle.facts == []


def test_undatable_events_are_skipped_not_fatal() -> None:
    events = [
        _event(record_id="1", event_id=1),
        {"EventID": 1, "Channel": "X", "EventRecordID": "2", "Computer": "ws-01"},
    ]
    bundle = build_spike_bundle(events, anchor_time=ANCHOR)
    assert len(bundle.facts) == 1
