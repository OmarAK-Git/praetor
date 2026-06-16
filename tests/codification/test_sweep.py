"""TASK-034: empirical org-config sweep prototype."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from praetor.codification import (
    PROPOSED_ARTIFACT_KIND,
    is_proposed_org_config_artifact,
    render_proposed_org_config_yaml,
    render_sweep_report_markdown,
    run_org_config_sweep,
)
from praetor.config.errors import PreflightError
from praetor.config.preflight import run_preflight
from praetor.correlation import load_fixture_events

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


def test_sweep_summarizes_observations_from_fixtures() -> None:
    result = _fixture_sweep()

    principals = {item.principal_id: item for item in result.summary.principals}
    assert principals["corp\\jdoe"].observation_count == 3
    assert principals["corp\\jdoe"].sources == frozenset(
        {"sysmon_user", "security_account"}
    )

    assets = {item.asset_id: item for item in result.summary.assets}
    assert assets["workstation1"].observation_count == 3

    patterns = {item.name: item for item in result.summary.admin_patterns}
    assert patterns["sweep_observed_explorer_to_cmd"].observation_count == 1
    assert patterns["sweep_observed_cmd_to_powershell"].observation_count == 1

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


def test_report_documents_coverage_limits() -> None:
    result = _fixture_sweep()
    markdown = render_sweep_report_markdown(result.report)

    assert "Coverage limits" in markdown
    assert "EventID 1" in markdown
    assert "EventID 4624" in markdown
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
    assert "UNOBSERVED-REQUIRES-HUMAN-REVIEW" in markdown


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
