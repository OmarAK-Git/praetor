"""TASK-028: correlation normalization and PromptExcerptSet."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from praetor.contracts.evidence import EvidenceBundle
from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.correlation.entities import assemble_process_relationships
from praetor.correlation.security_log import normalize_security_event
from praetor.correlation.sysmon import normalize_sysmon_event
from praetor.evidence.provenance import (
    SYSMON_EVENT_LOG,
    WINDOWS_SECURITY_LOG,
    meets_account_corroboration,
)
from praetor.judgment.excerpt import MAX_PROMPT_EXCERPT_CHARS
from praetor.policy.containment_policy import (
    extract_account_identity,
    resolve_host_target,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SYSMON_FIXTURES = FIXTURES / "sysmon"
SECURITY_FIXTURES = FIXTURES / "security"
ANCHOR = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


def _load_json_fixture(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_fixture_events(payload)


def _correlate_fixture_scenario() -> tuple:
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    sysmon_events.extend(
        _load_json_fixture(SYSMON_FIXTURES / "noise_outside_window.json")
    )
    security_events = _load_json_fixture(
        SECURITY_FIXTURES / "successful_logon_4624.json"
    )
    return correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=ANCHOR,
    )


def test_sysmon_process_creation_normalizes() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    fact = normalize_sysmon_event(events[0])

    assert fact.provenance_path == SYSMON_EVENT_LOG
    assert fact.ambiguity_flag is False
    assert fact.normalized_fields["process_name"] == "cmd.exe"
    assert fact.normalized_fields["user"] == "CORP\\jdoe"
    assert fact.normalized_fields["process_guid"] == (
        "{11111111-1111-1111-1111-111111111111}"
    )
    assert fact.normalized_fields["host_id"] == "WORKSTATION1"
    assert fact.source_event_reference.startswith("microsoft-windows-sysmon:")


def test_sysmon_normalized_fields_omit_eventdata_clock_strings() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    events[0] = {
        **events[0],
        "EventData": {
            **events[0]["EventData"],
            "NewTime": "2026-06-08T12:00:00.1234567Z",
            "PreviousTime": "2026-06-08T11:59:59.7654321Z",
        },
    }
    fact = normalize_sysmon_event(events[0])

    assert "NewTime" not in fact.normalized_fields
    assert "PreviousTime" not in fact.normalized_fields
    hashed_values = [str(v) for v in fact.normalized_fields.values()]
    assert not any("1234567" in value or "7654321" in value for value in hashed_values)


def test_security_logon_normalizes() -> None:
    events = _load_json_fixture(SECURITY_FIXTURES / "successful_logon_4624.json")
    fact = normalize_security_event(events[0])

    assert fact.provenance_path == WINDOWS_SECURITY_LOG
    assert fact.ambiguity_flag is False
    assert fact.normalized_fields["account_name"] == "jdoe"
    assert fact.normalized_fields["domain"] == "CORP"
    assert fact.normalized_fields["host_id"] == "WORKSTATION1"
    assert fact.normalized_fields["target_sid"].startswith("S-1-5-21-")
    assert fact.source_event_reference.startswith("security:4624:")


def test_every_fact_has_raw_source() -> None:
    result = _correlate_fixture_scenario()

    assert result.bundle.facts
    for fact in result.bundle.facts:
        assert fact.raw_source
        assert json.loads(fact.raw_source)


def test_prompt_excerpt_set_is_bounded_and_raw_source_free() -> None:
    result = _correlate_fixture_scenario()
    payload = result.prompt_excerpt_set.as_provider_payload()
    serialized = json.dumps(payload)

    assert "raw_source" not in serialized
    assert result.prompt_excerpt_set.facts
    for fact in result.prompt_excerpt_set.facts:
        for excerpt in fact.excerpts:
            assert len(excerpt.text) <= MAX_PROMPT_EXCERPT_CHARS


def test_parent_child_process_relationships() -> None:
    result = _correlate_fixture_scenario()
    graph = assemble_process_relationships(result.bundle.facts)

    parent = graph.entities["{11111111-1111-1111-1111-111111111111}"]
    child = graph.entities["{22222222-2222-2222-2222-222222222222}"]

    assert parent.process_name == "cmd.exe"
    assert child.parent_process_guid == parent.process_guid
    assert graph.parent_of(child.process_guid) == parent
    assert graph.children_of(parent.process_guid) == (child,)


def test_time_window_excludes_noise() -> None:
    result = _correlate_fixture_scenario()
    references = {fact.source_event_reference for fact in result.bundle.facts}

    assert any("1001" in ref for ref in references)
    assert any("1002" in ref for ref in references)
    assert any("2001" in ref for ref in references)
    assert all("9999" not in ref for ref in references)


def test_ambiguous_user_sets_ambiguity_flag() -> None:
    events = _load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json")
    fact = normalize_sysmon_event(events[0])

    assert fact.ambiguity_flag is True
    assert fact.normalized_fields["user"] == "jdoe"


def test_correlation_consumers_resolve_fixture_scenario() -> None:
    result = _correlate_fixture_scenario()

    host_target = resolve_host_target(result.bundle)
    assert host_target is not None
    assert host_target.target_id == "WORKSTATION1"

    identity = extract_account_identity(result.bundle.facts)
    assert identity is not None
    assert identity.domain == "CORP"

    assert meets_account_corroboration(result.bundle.facts) is True


def test_correlate_skips_unsupported_sysmon_event_ids() -> None:
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    sysmon_events.append(
        {
            "record_id": "3001",
            "@timestamp": "2026-06-08T12:00:02.000000Z",
            "EventID": 3,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "Computer": "WORKSTATION1",
            "EventData": {
                "ProcessGuid": "{aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa}",
                "DestinationIp": "10.0.0.1",
                "DestinationPort": "443",
            },
        }
    )
    security_events = _load_json_fixture(
        SECURITY_FIXTURES / "successful_logon_4624.json"
    )

    result = correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=ANCHOR,
    )

    assert len(result.bundle.facts) == 3
    event_ids = {
        json.loads(fact.raw_source)["EventID"] for fact in result.bundle.facts
    }
    assert event_ids == {1, 4624}


def test_correlation_bundle_validates() -> None:
    result = _correlate_fixture_scenario()
    round_trip = EvidenceBundle.model_validate(result.bundle.model_dump(mode="json"))
    assert len(round_trip.facts) == 3


def test_fixture_manifest_registers_checksums() -> None:
    manifest_path = FIXTURES / "fixture_manifest.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    assert data["fixtures"]
    for entry in data["fixtures"]:
        rel_path = entry["path"]
        expected = entry["sha256"]
        content = (FIXTURES.parent / rel_path).read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        assert actual == expected
