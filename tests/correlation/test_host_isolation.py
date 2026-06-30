"""V2-014: correlator anchor-host isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.correlation.host_isolation import (
    event_host_id,
    filter_events_to_anchor_host,
    resolve_anchor_host_id,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SYSMON_FIXTURES = FIXTURES / "sysmon"
SECURITY_FIXTURES = FIXTURES / "security"
ANCHOR = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


def _load_json_fixture(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_fixture_events(payload)


def test_resolve_anchor_host_uses_plurality_against_cross_host_noise() -> None:
    sysmon = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    sysmon.extend(
        _load_json_fixture(SYSMON_FIXTURES / "noise_in_window_unrelated.json")
    )
    security = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")

    assert (
        resolve_anchor_host_id(
            sysmon_events=sysmon,
            security_events=security,
            anchor_time=ANCHOR,
        )
        == "WORKSTATION1"
    )


def test_resolve_anchor_host_ignores_security_event_ordering() -> None:
    sysmon = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    security = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")
    unrelated_security = {
        "record_id": "2999",
        "@timestamp": "2026-06-08T11:59:30.000000Z",
        "EventID": 4624,
        "Channel": "Security",
        "Computer": "WORKSTATION2",
        "EventData": {
            "TargetUserName": "otheruser",
            "TargetDomainName": "OTHERCORP",
            "TargetSid": "S-1-5-21-9999999999-999999999-999999999-2002",
            "LogonType": "2",
            "IpAddress": "10.0.0.99",
        },
    }
    security = [unrelated_security, *security]

    assert (
        resolve_anchor_host_id(
            sysmon_events=sysmon,
            security_events=security,
            anchor_time=ANCHOR,
        )
        == "WORKSTATION1"
    )


def test_correlate_keeps_incident_when_unrelated_security_is_first() -> None:
    sysmon = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    security = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")
    unrelated_security = {
        "record_id": "2999",
        "@timestamp": "2026-06-08T11:59:30.000000Z",
        "EventID": 4624,
        "Channel": "Security",
        "Computer": "WORKSTATION2",
        "EventData": {
            "TargetUserName": "otheruser",
            "TargetDomainName": "OTHERCORP",
            "TargetSid": "S-1-5-21-9999999999-999999999-999999999-2002",
            "LogonType": "2",
            "IpAddress": "10.0.0.99",
        },
    }
    security = [unrelated_security, *security]

    result = correlate_telemetry(
        sysmon_events=sysmon,
        security_events=security,
        anchor_time=ANCHOR,
    )

    record_ids = {
        json.loads(fact.raw_source)["record_id"] for fact in result.bundle.facts
    }
    assert record_ids == {"1001", "1002", "2001"}
    host_ids = {
        fact.normalized_fields.get("host_id") for fact in result.bundle.facts
    }
    assert host_ids == {"WORKSTATION1"}


def test_resolve_anchor_host_explicit_override() -> None:
    sysmon = _load_json_fixture(SYSMON_FIXTURES / "noise_in_window_unrelated.json")
    assert (
        resolve_anchor_host_id(
            sysmon_events=sysmon,
            security_events=[],
            anchor_host_id="WORKSTATION2",
        )
        == "WORKSTATION2"
    )


def test_correlate_drops_cross_host_in_window_noise() -> None:
    sysmon = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    sysmon.extend(_load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json"))
    sysmon.extend(
        _load_json_fixture(SYSMON_FIXTURES / "noise_in_window_unrelated.json")
    )
    security = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")

    result = correlate_telemetry(
        sysmon_events=sysmon,
        security_events=security,
        anchor_time=ANCHOR,
    )

    record_ids = {
        json.loads(fact.raw_source)["record_id"] for fact in result.bundle.facts
    }
    assert record_ids == {"1001", "1002", "1003", "2001"}
    assert "1004" not in record_ids

    host_ids = {
        fact.normalized_fields.get("host_id") for fact in result.bundle.facts
    }
    assert host_ids == {"WORKSTATION1"}


def test_correlate_retains_same_host_incidental_noise() -> None:
    sysmon = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    sysmon.extend(_load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json"))
    security = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")

    result = correlate_telemetry(
        sysmon_events=sysmon,
        security_events=security,
        anchor_time=ANCHOR,
    )

    record_ids = {
        json.loads(fact.raw_source)["record_id"] for fact in result.bundle.facts
    }
    assert "1003" in record_ids


def test_filter_events_to_anchor_host() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    events.extend(
        _load_json_fixture(SYSMON_FIXTURES / "noise_in_window_unrelated.json")
    )

    scoped = filter_events_to_anchor_host(events, anchor_host_id="WORKSTATION1")
    assert len(scoped) == 2
    assert all(event_host_id(event) == "WORKSTATION1" for event in scoped)


def _symmetric_host_events(
    host_id: str,
    *,
    record_prefix: str,
) -> tuple[dict, dict]:
    timestamp = "2026-06-08T12:00:00.000000Z"
    sysmon = {
        "record_id": f"{record_prefix}-sysmon",
        "@timestamp": timestamp,
        "EventID": 1,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": host_id,
        "EventData": {
            "ProcessGuid": f"{{{record_prefix}-sysmon-guid}}",
            "ProcessId": "1111",
            "Image": "C:\\Windows\\System32\\cmd.exe",
            "CommandLine": "cmd.exe",
            "User": "CORP\\user",
            "ParentProcessGuid": "{00000000-0000-0000-0000-000000000099}",
            "ParentProcessId": "1100",
            "ParentImage": "C:\\Windows\\explorer.exe",
        },
    }
    security = {
        "record_id": f"{record_prefix}-security",
        "@timestamp": timestamp,
        "EventID": 4624,
        "Channel": "Security",
        "Computer": host_id,
        "EventData": {
            "TargetUserName": "user",
            "TargetDomainName": "CORP",
            "TargetSid": f"S-1-5-21-{record_prefix}",
            "LogonType": "2",
            "IpAddress": "10.0.0.10",
        },
    }
    return sysmon, security


def test_resolve_anchor_host_returns_none_when_rank_is_ambiguous() -> None:
    host_a_sysmon, host_a_security = _symmetric_host_events(
        "HOST-A",
        record_prefix="a",
    )
    host_b_sysmon, host_b_security = _symmetric_host_events(
        "HOST-B",
        record_prefix="b",
    )

    assert (
        resolve_anchor_host_id(
            sysmon_events=[host_a_sysmon, host_b_sysmon],
            security_events=[host_a_security, host_b_security],
            anchor_time=ANCHOR,
        )
        is None
    )


def test_correlate_skips_host_filter_when_anchor_is_ambiguous() -> None:
    host_a_sysmon, host_a_security = _symmetric_host_events(
        "HOST-A",
        record_prefix="a",
    )
    host_b_sysmon, host_b_security = _symmetric_host_events(
        "HOST-B",
        record_prefix="b",
    )

    result = correlate_telemetry(
        sysmon_events=[host_a_sysmon, host_b_sysmon],
        security_events=[host_a_security, host_b_security],
        anchor_time=ANCHOR,
    )

    host_ids = {
        fact.normalized_fields.get("host_id") for fact in result.bundle.facts
    }
    assert host_ids == {"HOST-A", "HOST-B"}
