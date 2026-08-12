from __future__ import annotations

from datetime import UTC, datetime

from evals.capability.flatten import (
    SPIKE_UNKNOWN_SOURCE,
    flatten_event_to_fact,
    resolve_provenance_path,
)

from praetor.evidence.provenance import SYSMON_EVENT_LOG, WINDOWS_SECURITY_LOG

SYSMON_NETWORK_EVENT = {
    "EventID": 3,
    "Channel": "Microsoft-Windows-Sysmon/Operational",
    "EventRecordID": "9001",
    "Computer": "ws-01",
    "UtcTime": "2026-01-01 12:00:00.000",
    "EventData": {
        "Image": r"C:\Windows\System32\powershell.exe",
        "DestinationIp": "203.0.113.10",
        "DestinationPort": "443",
    },
}


def test_unsupported_event_id_still_produces_a_fact() -> None:
    """EventID 3 is rejected by correlation but must flatten cleanly here."""
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.provenance_path == SYSMON_EVENT_LOG
    assert fact.evidence_id.startswith("ev-")
    assert fact.timestamp == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_event_data_is_flattened_into_normalized_fields() -> None:
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.normalized_fields["DestinationIp"] == "203.0.113.10"
    assert fact.normalized_fields["DestinationPort"] == "443"
    assert fact.normalized_fields["Image"].endswith("powershell.exe")
    # Citation-mix join key must survive flattening.
    assert fact.normalized_fields["EventID"] == 3
    assert fact.normalized_fields["Channel"] == (
        "Microsoft-Windows-Sysmon/Operational"
    )


def test_host_id_key_is_set_for_targeting() -> None:
    """host_id is the silent contract with containment_policy consumers."""
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.normalized_fields["host_id"] == "ws-01"


def test_raw_source_key_excluded_from_normalized_fields() -> None:
    """excerpt.py skips a normalized_fields['raw_source'] key; never emit one."""
    event = dict(SYSMON_NETWORK_EVENT)
    event["raw_source"] = "must not appear in normalized_fields"
    fact = flatten_event_to_fact(event, provenance_path=SYSMON_EVENT_LOG)
    assert "raw_source" not in fact.normalized_fields
    assert "must not appear" in fact.raw_source


def test_source_event_reference_includes_record_id() -> None:
    """Enrichment counts distinct source_event_reference, so record_id matters."""
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.source_event_reference.endswith(":3:9001")


def test_two_records_of_same_event_id_are_distinct_source_events() -> None:
    second = dict(SYSMON_NETWORK_EVENT)
    second["EventRecordID"] = "9002"
    a = flatten_event_to_fact(SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG)
    b = flatten_event_to_fact(second, provenance_path=SYSMON_EVENT_LOG)
    assert a.source_event_reference != b.source_event_reference
    assert a.evidence_id != b.evidence_id


def test_resolve_provenance_path_by_channel() -> None:
    assert resolve_provenance_path(SYSMON_NETWORK_EVENT) == SYSMON_EVENT_LOG
    assert (
        resolve_provenance_path({"Channel": "Security", "EventID": 4688})
        == WINDOWS_SECURITY_LOG
    )
    assert (
        resolve_provenance_path({"Channel": "SomeVendor/EDR", "EventID": 7})
        == SPIKE_UNKNOWN_SOURCE
    )


def test_ambiguity_flag_defaults_false() -> None:
    fact = flatten_event_to_fact(
        SYSMON_NETWORK_EVENT, provenance_path=SYSMON_EVENT_LOG
    )
    assert fact.ambiguity_flag is False


def test_seven_digit_eventdata_timestamps_are_canonicalized() -> None:
    """Security 4616 NewTime/PreviousTime use 100ns (7-digit) fractions."""
    from praetor.hashing.canonical import canonical_serialize

    event = {
        "EventID": 4616,
        "Channel": "Security",
        "EventRecordID": "42",
        "Computer": "ws-01",
        "UtcTime": "2022-07-19 17:24:49.641",
        "EventData": {
            "NewTime": "2022-07-19T17:24:49.6410000Z",
            "PreviousTime": "2022-07-19T12:24:47.1110294Z",
        },
    }
    fact = flatten_event_to_fact(event, provenance_path=WINDOWS_SECURITY_LOG)
    assert fact.normalized_fields["NewTime"] == "2022-07-19T17:24:49.641000Z"
    assert fact.normalized_fields["PreviousTime"] == (
        "2022-07-19T12:24:47.111029Z"
    )
    # Bundle hashing walks normalized_fields; must not raise.
    canonical_serialize(fact.model_dump(mode="python"))
