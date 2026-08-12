from __future__ import annotations

from datetime import UTC, datetime

from evals.capability.bundle import (
    PATH_B_MAX_FACTS,
    PATH_B_MAX_PER_EVENT_ID,
    assert_path_b_superset_of_path_a,
    build_spike_bundle,
    build_spike_bundle_result,
)

from praetor.correlation import correlate_telemetry

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


def test_path_b_extras_cap_binds_without_dropping_path_a() -> None:
    path_a = [
        _event(record_id=f"a{i}", event_id=1, utc=f"2026-01-01 12:00:{i:02d}.000")
        for i in range(40)
    ]
    extras = [
        _event(
            record_id=f"x{i}",
            event_id=4663,
            channel="Security",
            utc=f"2026-01-01 12:00:{i % 60:02d}.500",
        )
        for i in range(200)
    ]
    result = build_spike_bundle_result(
        [*path_a, *extras],
        anchor_time=ANCHOR,
        window_seconds=3600,
        max_facts=80,
        max_extra_facts=20,
    )
    assert result.path_a_event_count == 40
    assert result.extras_selected == 20
    assert len(result.bundle.facts) == 60
    assert result.cap_bound is True
    eids = [fact.normalized_fields.get("EventID") for fact in result.bundle.facts]
    assert eids.count(1) == 40


def test_path_b_default_extras_budget_is_constant() -> None:
    from evals.capability.bundle import PATH_B_EXTRAS_BUDGET

    path_a = [
        _event(record_id=f"a{i}", event_id=1, utc=f"2026-01-01 12:00:{i:02d}.000")
        for i in range(30)
    ]
    extras = [
        _event(
            record_id=f"x{i}",
            event_id=4663,
            channel="Security",
            utc=f"2026-01-01 12:01:{i % 60:02d}.000",
        )
        for i in range(400)
    ]
    result = build_spike_bundle_result(
        [*path_a, *extras],
        anchor_time=ANCHOR,
        window_seconds=3600,
    )
    # Seed not set — extras_selected == PATH_B_EXTRAS_BUDGET exactly.
    assert result.extras_selected == PATH_B_EXTRAS_BUDGET
    assert len(result.bundle.facts) == 30 + PATH_B_EXTRAS_BUDGET
    assert result.cap_bound is True
    # Safety ceiling must not bind for this density.
    assert len(result.bundle.facts) < PATH_B_MAX_FACTS


def test_path_b_stratified_extras_limit_per_event_id() -> None:
    events = [
        _event(
            record_id=f"e{eid}-{i}",
            event_id=4000 + eid,
            utc=f"2026-01-01 12:00:{(eid * 3 + i) % 60:02d}.{eid:03d}",
        )
        for eid in range(16)
        for i in range(10)
    ]
    result = build_spike_bundle_result(
        events,
        anchor_time=ANCHOR,
        window_seconds=3600,
        max_facts=64,
        max_extra_facts=64,
    )
    assert len(result.bundle.facts) == 64
    eids = [
        fact.normalized_fields.get("EventID") for fact in result.bundle.facts
    ]
    for eid in set(eids):
        assert eids.count(eid) <= PATH_B_MAX_PER_EVENT_ID


def test_path_b_always_retains_seed_record() -> None:
    storm = [
        _event(
            record_id=str(i),
            event_id=4663,
            channel="Security",
            utc=f"2026-01-01 12:00:{i % 60:02d}.000",
        )
        for i in range(200)
    ]
    seed = _event(
        record_id="seed-1",
        event_id=4688,
        channel="Security",
        utc="2026-01-01 12:04:50.000",
    )
    result = build_spike_bundle_result(
        [*storm, seed],
        anchor_time=ANCHOR,
        window_seconds=3600,
        seed_event_record_id="seed-1",
        seed_host_id="ws-01",
        max_facts=64,
        max_extra_facts=64,
    )
    assert result.seed_retained is True
    refs = {fact.source_event_reference for fact in result.bundle.facts}
    assert any("seed-1" in ref for ref in refs)


def test_path_b_is_superset_of_path_a_by_construction() -> None:
    events = [
        *(
            _event(
                record_id=f"s{i}",
                event_id=1,
                utc=f"2026-01-01 12:00:{i:02d}.000",
            )
            for i in range(30)
        ),
        *(
            _event(
                record_id=f"l{i}",
                event_id=4624,
                channel="Security",
                utc=f"2026-01-01 12:00:{i:02d}.100",
            )
            for i in range(5)
        ),
        *(
            _event(
                record_id=f"n{i}",
                event_id=4663,
                channel="Security",
                utc=f"2026-01-01 12:01:{i % 60:02d}.200",
            )
            for i in range(100)
        ),
    ]
    path_a = correlate_telemetry(
        sysmon_events=[e for e in events if "sysmon" in str(e["Channel"]).lower()],
        security_events=[
            e for e in events if str(e["Channel"]).lower().startswith("security")
        ],
        anchor_time=ANCHOR,
        anchor_host_id="ws-01",
        window_seconds=3600,
    ).bundle
    path_b = build_spike_bundle_result(
        events,
        anchor_time=ANCHOR,
        anchor_host_id="ws-01",
        window_seconds=3600,
        max_facts=PATH_B_MAX_FACTS,
        max_extra_facts=40,
    )
    assert len(path_b.bundle.facts) > len(path_a.facts)
    assert_path_b_superset_of_path_a(path_a, path_b.bundle, anchor_id="t")
