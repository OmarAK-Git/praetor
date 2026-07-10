"""V2-027: org-config sweep operator CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from praetor.codification.cli import SWEEP_LIMITATIONS_EPILOG
from praetor.config.errors import PreflightError
from praetor.config.preflight import run_preflight

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SYSMON_FIXTURE = FIXTURES / "sysmon" / "process_chain.json"
SECURITY_FIXTURE = FIXTURES / "security" / "successful_logon_4624.json"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "praetor.codification", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_sweep_cli_help_documents_limitations() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0, result.stderr or result.stdout
    help_text = result.stdout
    assert "never-contain" in help_text.lower()
    assert "subnet membership" in help_text.lower()
    assert "containment policy" in help_text.lower()
    assert SWEEP_LIMITATIONS_EPILOG.splitlines()[0] in help_text


def test_sweep_cli_writes_yaml_and_report() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        yaml_path = out_dir / "proposed.yaml"
        report_path = out_dir / "report.md"
        result = _run_cli(
            "--org-id",
            "cli-review-org",
            "--sysmon",
            str(SYSMON_FIXTURE),
            "--security",
            str(SECURITY_FIXTURE),
            "--output-yaml",
            str(yaml_path),
            "--output-report",
            str(report_path),
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert yaml_path.is_file()
        assert report_path.is_file()

        parsed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert parsed["version_metadata"]["org_id"] == "cli-review-org"
        assert parsed["known_principals"]["observed_principals"]
        assert parsed["assets_and_asset_groups"]["entries"]

        report_text = report_path.read_text(encoding="utf-8")
        assert "# Org-Config Sweep Report" in report_text
        assert "Coverage limits" in report_text


def test_sweep_cli_output_fails_preflight() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        yaml_path = out_dir / "proposed.yaml"
        report_path = out_dir / "report.md"
        result = _run_cli(
            "--org-id",
            "preflight-org",
            "--sysmon",
            str(SYSMON_FIXTURE),
            "--security",
            str(SECURITY_FIXTURE),
            "--output-yaml",
            str(yaml_path),
            "--output-report",
            str(report_path),
        )
        assert result.returncode == 0, result.stderr or result.stdout

        proposed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        yaml_text = yaml_path.read_text(encoding="utf-8")
        with pytest.raises(PreflightError) as exc_info:
            run_preflight(proposed, verbatim_text=yaml_text)
        assert exc_info.value.code == "proposed_artifact_not_activatable"


def test_sweep_cli_exits_nonzero_missing_org_id() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        result = _run_cli(
            "--sysmon",
            str(SYSMON_FIXTURE),
            "--output-yaml",
            str(out_dir / "proposed.yaml"),
            "--output-report",
            str(out_dir / "report.md"),
        )
        assert result.returncode != 0
        assert "org-id" in (result.stderr + result.stdout).lower()


def test_sweep_cli_exits_nonzero_blank_org_id() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        result = _run_cli(
            "--org-id",
            "   ",
            "--output-yaml",
            str(out_dir / "proposed.yaml"),
            "--output-report",
            str(out_dir / "report.md"),
        )
        assert result.returncode != 0
        assert "non-empty" in result.stderr.lower()


def test_sweep_cli_exits_nonzero_missing_telemetry_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        result = _run_cli(
            "--org-id",
            "missing-file-org",
            "--sysmon",
            str(out_dir / "does-not-exist.json"),
            "--output-yaml",
            str(out_dir / "proposed.yaml"),
            "--output-report",
            str(out_dir / "report.md"),
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()


def test_sweep_cli_exits_nonzero_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        bad_json = out_dir / "bad.json"
        bad_json.write_text("{not-json", encoding="utf-8")
        result = _run_cli(
            "--org-id",
            "bad-json-org",
            "--sysmon",
            str(bad_json),
            "--output-yaml",
            str(out_dir / "proposed.yaml"),
            "--output-report",
            str(out_dir / "report.md"),
        )
        assert result.returncode != 0
        assert "invalid json" in result.stderr.lower()


def test_sweep_cli_exits_nonzero_invalid_fixture_shape() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        invalid_fixture = out_dir / "invalid.json"
        invalid_fixture.write_text(
            json.dumps({"events": "not-a-list"}),
            encoding="utf-8",
        )
        result = _run_cli(
            "--org-id",
            "invalid-fixture-org",
            "--sysmon",
            str(invalid_fixture),
            "--output-yaml",
            str(out_dir / "proposed.yaml"),
            "--output-report",
            str(out_dir / "report.md"),
        )
        assert result.returncode != 0
        assert "invalid telemetry fixture" in result.stderr.lower()
