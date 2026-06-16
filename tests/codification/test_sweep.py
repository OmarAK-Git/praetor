"""TASK-034: empirical org-config sweep prototype."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from praetor.codification import (
    PROPOSED_ARTIFACT_KIND,
    REPLACE_BEFORE_ACTIVATION_NEVER_CONTAIN_TARGET,
    UNOBSERVED_SUBNET_PLACEHOLDER,
    ZERO_EVIDENCE_ACTIVATION_STATUS,
    is_proposed_org_config_artifact,
    render_proposed_org_config_yaml,
    render_sweep_report_markdown,
    run_org_config_sweep,
    telemetry_coverage_event_ids,
)
from praetor.config.errors import PreflightError
from praetor.config.preflight import run_preflight
from praetor.correlation import load_fixture_events
from praetor.correlation.security_log import SUPPORTED_SECURITY_EVENT_IDS
from praetor.correlation.sysmon import SUPPORTED_SYSMON_EVENT_IDS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SYSMON_FIXTURES = FIXTURES / "sysmon"
SECURITY_FIXTURES = FIXTURES / "security"


def _load_json_fixture(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_fixture_events(payload)


def _fixture_sweep(*, org_id: str = "example-corp"):
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    security_events = _load_json_fixture(
        SECURITY_FIXTURES / "successful_logon_4624.json"
    )
    return run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=security_events,
        org_id=org_id,
    )


def _activation_ready_config(proposed: dict) -> dict:
    config = copy.deepcopy(proposed)
    metadata = config["version_metadata"]
    metadata.pop("artifact_kind", None)
    metadata.pop("activation_status", None)
    metadata.pop("artifact_usable", None)
    config["assets_and_asset_groups"]["entries"][0]["subnet_membership"] = (
        "10.0.0.0/24"
    )
    config["containment_exclusions"]["never_contain"][0]["target_id"] = "backup-gateway"
    return config


def test_sweep_summarizes_observations_from_fixtures() -> None:
    result = _fixture_sweep()

    principals = {item.principal_id: item for item in result.summary.principals}
    assert principals["corp\\jdoe"].observation_count == 3
    assert principals["corp\\jdoe"].ambiguous_observation_count == 0
    assert principals["corp\\jdoe"].sources == frozenset(
        {"sysmon_user", "security_account"}
    )

    assets = {item.asset_id: item for item in result.summary.assets}
    assert assets["workstation1"].observation_count == 3

    patterns = {item.name: item for item in result.summary.admin_patterns}
    explorer_cmd = patterns["sweep_observed_workstation1_corp_jdoe_explorer_to_cmd"]
    assert explorer_cmd.observation_count == 1
    assert (
        patterns["sweep_observed_workstation1_corp_jdoe_cmd_to_powershell"].observation_count
        == 1
    )

    counts = result.summary.event_counts
    assert counts.sysmon_events_seen == 2
    assert counts.sysmon_events_normalized == 2
    assert counts.security_events_normalized == 1


def test_proposed_artifact_rejected_by_preflight() -> None:
    result = _fixture_sweep()
    proposed = result.proposed_config

    assert is_proposed_org_config_artifact(proposed)
    assert proposed["version_metadata"]["artifact_kind"] == PROPOSED_ARTIFACT_KIND
    assert (
        proposed["version_metadata"]["activation_status"]
        == "proposed_for_review_only"
    )

    yaml_text = render_proposed_org_config_yaml(proposed)
    with pytest.raises(PreflightError) as exc_info:
        run_preflight(proposed, verbatim_text=yaml_text)
    assert exc_info.value.code == "proposed_artifact_not_activatable"


def test_marker_stripped_placeholder_artifact_rejected_by_preflight() -> None:
    result = _fixture_sweep()
    stripped = copy.deepcopy(result.proposed_config)
    stripped["version_metadata"].pop("artifact_kind")

    assert not is_proposed_org_config_artifact(stripped)
    assert (
        stripped["assets_and_asset_groups"]["entries"][0]["subnet_membership"]
        == UNOBSERVED_SUBNET_PLACEHOLDER
    )
    assert (
        stripped["containment_exclusions"]["never_contain"][0]["target_id"]
        == REPLACE_BEFORE_ACTIVATION_NEVER_CONTAIN_TARGET
    )

    yaml_text = render_proposed_org_config_yaml(stripped)
    with pytest.raises(PreflightError) as exc_info:
        run_preflight(stripped, verbatim_text=yaml_text)
    assert exc_info.value.code == "unreplaced_sweep_placeholder"


def test_placeholders_replaced_artifact_passes_preflight() -> None:
    result = _fixture_sweep()
    ready = _activation_ready_config(result.proposed_config)
    yaml_text = render_proposed_org_config_yaml(ready)

    snapshot = run_preflight(ready, verbatim_text=yaml_text)
    assert snapshot.version_metadata.org_id == "example-corp"


def test_preflight_marker_matches_canonical_constant() -> None:
    assert PROPOSED_ARTIFACT_KIND == "proposed_org_config"
    proposed = _fixture_sweep().proposed_config
    assert proposed["version_metadata"]["artifact_kind"] == PROPOSED_ARTIFACT_KIND
    with pytest.raises(PreflightError) as exc_info:
        run_preflight(proposed, verbatim_text=render_proposed_org_config_yaml(proposed))
    assert exc_info.value.code == "proposed_artifact_not_activatable"


def test_report_telemetry_coverage_matches_normalizer_event_ids() -> None:
    result = _fixture_sweep()
    markdown = render_sweep_report_markdown(result.report)
    sysmon_ids, security_ids = telemetry_coverage_event_ids()

    assert sysmon_ids == SUPPORTED_SYSMON_EVENT_IDS
    assert security_ids == SUPPORTED_SECURITY_EVENT_IDS

    telemetry_limit = next(
        item
        for item in result.report.coverage_limits
        if item.code == "telemetry_sources"
    )
    for event_id in sorted(sysmon_ids):
        assert f"EventID {event_id}" in telemetry_limit.description
    for event_id in sorted(security_ids):
        assert f"EventID {event_id}" in telemetry_limit.description
    assert "EventID 1" in markdown
    assert "EventID 4624" in markdown


def test_report_documents_coverage_limits() -> None:
    result = _fixture_sweep()
    markdown = render_sweep_report_markdown(result.report)

    assert "Coverage limits" in markdown
    assert "Sysmon seen=2" in markdown
    assert "Security seen=1" in markdown
    assert result.summary.earliest_timestamp is not None


def test_report_documents_absence_of_evidence_risks() -> None:
    result = _fixture_sweep()
    markdown = render_sweep_report_markdown(result.report)
    risk_codes = {item.code for item in result.report.absence_of_evidence_risks}

    assert "Absence-of-evidence risks" in markdown
    assert "subnet_membership_unobserved" in risk_codes
    assert "never_contain_not_inferred" in risk_codes
    assert "admin_patterns_heuristic" in risk_codes
    assert UNOBSERVED_SUBNET_PLACEHOLDER in markdown


def test_empty_telemetry_produces_unusable_zero_evidence_artifact() -> None:
    result = run_org_config_sweep(
        sysmon_events=[],
        security_events=[],
        org_id="empty-org",
    )

    assert not result.summary.has_normalized_evidence
    assert result.summary.principals == ()
    assert result.summary.assets == ()
    assert result.summary.admin_patterns == ()

    proposed = result.proposed_config
    assert (
        proposed["version_metadata"]["activation_status"]
        == ZERO_EVIDENCE_ACTIVATION_STATUS
    )
    assert proposed["version_metadata"]["artifact_usable"] is False
    assert proposed["assets_and_asset_groups"]["entries"] == []

    markdown = render_sweep_report_markdown(result.report)
    assert "zero normalized evidence" in markdown.lower()
    assert "zero_normalized_evidence" in {
        item.code for item in result.report.absence_of_evidence_risks
    }

    counts = result.summary.event_counts
    assert counts.sysmon_events_seen == 0
    assert counts.sysmon_events_normalized == 0
    assert counts.security_events_normalized == 0


def test_all_skipped_telemetry_reports_seen_but_not_normalized() -> None:
    sysmon_events = [
        {
            "record_id": "9001",
            "@timestamp": "2026-06-08T12:00:00.000000Z",
            "EventID": 3,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "Computer": "WORKSTATION9",
        }
    ]
    security_events = [
        {
            "record_id": "9002",
            "@timestamp": "2026-06-08T12:00:01.000000Z",
            "EventID": 4625,
            "Channel": "Security",
            "Computer": "WORKSTATION9",
        }
    ]
    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=security_events,
        org_id="skipped-org",
    )

    counts = result.summary.event_counts
    assert counts.sysmon_events_seen == 1
    assert counts.sysmon_events_normalized == 0
    assert counts.sysmon_events_skipped == 1
    assert counts.security_events_seen == 1
    assert counts.security_events_normalized == 0
    assert counts.security_events_skipped == 1
    assert not result.summary.has_normalized_evidence

    volume_limit = next(
        item for item in result.report.coverage_limits if item.code == "event_volume"
    )
    assert "normalized=0" in volume_limit.description
    assert "seen=1" in volume_limit.description


def test_ambiguous_sysmon_user_carried_into_principal_and_report() -> None:
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json")
    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=[],
        org_id="ambiguous-org",
    )

    principals = {item.principal_id: item for item in result.summary.principals}
    assert principals["jdoe"].observation_count == 1
    assert principals["jdoe"].ambiguous_observation_count == 1

    observed = result.proposed_config["known_principals"]["observed_principals"][0]
    assert observed["principal_id"] == "jdoe"
    assert observed["ambiguous_observation_count"] == 1

    risk_codes = {item.code for item in result.report.absence_of_evidence_risks}
    assert "principal_identity_ambiguous" in risk_codes
    markdown = render_sweep_report_markdown(result.report)
    assert "ambiguity_flag=true" in markdown


def test_domainless_sysmon_user_does_not_merge_with_domain_user() -> None:
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "ambiguous_user.json")
    sysmon_events.extend(_load_json_fixture(SYSMON_FIXTURES / "process_chain.json"))
    security_events = _load_json_fixture(
        SECURITY_FIXTURES / "successful_logon_4624.json"
    )
    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=security_events,
        org_id="identity-org",
    )

    principals = {item.principal_id: item for item in result.summary.principals}
    assert "jdoe" in principals
    assert "corp\\jdoe" in principals
    assert principals["jdoe"].observation_count == 1
    assert principals["corp\\jdoe"].observation_count == 3


def test_fqdn_security_domain_does_not_merge_with_netbios_sysmon_user() -> None:
    sysmon_events = _load_json_fixture(SYSMON_FIXTURES / "process_chain.json")
    security_events = [
        {
            "record_id": "3001",
            "@timestamp": "2026-06-08T12:00:02.000000Z",
            "EventID": 4624,
            "Channel": "Security",
            "Computer": "WORKSTATION1",
            "EventData": {
                "TargetUserName": "jdoe",
                "TargetDomainName": "corp.example.com",
                "TargetSid": "S-1-5-21-9999999999-999999999-999999999-1001",
                "LogonType": "2",
                "IpAddress": "10.0.0.20",
            },
        }
    ]
    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=security_events,
        org_id="fqdn-org",
    )

    principals = {item.principal_id: item for item in result.summary.principals}
    assert "corp\\jdoe" in principals
    assert "corp.example.com\\jdoe" in principals
    assert principals["corp\\jdoe"].observation_count == 2
    assert principals["corp.example.com\\jdoe"].observation_count == 1


def test_admin_patterns_unique_per_host_for_same_chain() -> None:
    sysmon_events = [
        {
            "record_id": "4001",
            "@timestamp": "2026-06-08T12:00:00.000000Z",
            "EventID": 1,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "Computer": "WORKSTATION1",
            "EventData": {
                "ProcessGuid": "{aaaa}",
                "ProcessId": "1",
                "Image": "C:\\Windows\\System32\\notepad.exe",
                "CommandLine": "notepad.exe",
                "User": "CORP\\jdoe",
                "ParentProcessGuid": "{bbbb}",
                "ParentProcessId": "2",
                "ParentImage": "C:\\Windows\\explorer.exe",
            },
        },
        {
            "record_id": "4002",
            "@timestamp": "2026-06-08T12:00:01.000000Z",
            "EventID": 1,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "Computer": "WORKSTATION2",
            "EventData": {
                "ProcessGuid": "{cccc}",
                "ProcessId": "3",
                "Image": "C:\\Windows\\System32\\notepad.exe",
                "CommandLine": "notepad.exe",
                "User": "CORP\\jdoe",
                "ParentProcessGuid": "{dddd}",
                "ParentProcessId": "4",
                "ParentImage": "C:\\Windows\\explorer.exe",
            },
        },
    ]
    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=[],
        org_id="multi-host-org",
    )

    pattern_names = [item.name for item in result.summary.admin_patterns]
    assert len(pattern_names) == 2
    assert len(set(pattern_names)) == 2
    assert "sweep_observed_workstation1_corp_jdoe_explorer_to_notepad" in pattern_names
    assert "sweep_observed_workstation2_corp_jdoe_explorer_to_notepad" in pattern_names


def test_admin_patterns_unique_per_user_on_same_host_and_chain() -> None:
    sysmon_events = [
        {
            "record_id": "5001",
            "@timestamp": "2026-06-08T12:00:00.000000Z",
            "EventID": 1,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "Computer": "WORKSTATION1",
            "EventData": {
                "ProcessGuid": "{eeee}",
                "ProcessId": "10",
                "Image": "C:\\Windows\\System32\\notepad.exe",
                "CommandLine": "notepad.exe",
                "User": "CORP\\jdoe",
                "ParentProcessGuid": "{ffff}",
                "ParentProcessId": "11",
                "ParentImage": "C:\\Windows\\explorer.exe",
            },
        },
        {
            "record_id": "5002",
            "@timestamp": "2026-06-08T12:00:01.000000Z",
            "EventID": 1,
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "Computer": "WORKSTATION1",
            "EventData": {
                "ProcessGuid": "{gggg}",
                "ProcessId": "12",
                "Image": "C:\\Windows\\System32\\notepad.exe",
                "CommandLine": "notepad.exe",
                "User": "CORP\\asmith",
                "ParentProcessGuid": "{hhhh}",
                "ParentProcessId": "13",
                "ParentImage": "C:\\Windows\\explorer.exe",
            },
        },
    ]
    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=[],
        org_id="multi-user-org",
    )

    pattern_names = [item.name for item in result.summary.admin_patterns]
    assert len(pattern_names) == 2
    assert len(set(pattern_names)) == 2
    assert "sweep_observed_workstation1_corp_jdoe_explorer_to_notepad" in pattern_names
    assert (
        "sweep_observed_workstation1_corp_asmith_explorer_to_notepad" in pattern_names
    )


def test_sweep_exposes_reviewable_artifact_and_report() -> None:
    result = _fixture_sweep(org_id="review-org")

    yaml_text = render_proposed_org_config_yaml(result.proposed_config)
    parsed = yaml.safe_load(yaml_text)
    assert parsed["version_metadata"]["org_id"] == "review-org"
    assert parsed["known_principals"]["observed_principals"]
    assert parsed["assets_and_asset_groups"]["entries"]
    assert parsed["normal_admin_patterns"]["patterns"]

    markdown = render_sweep_report_markdown(result.report)
    assert "SOC lead review" in markdown or "SOC review" in markdown
