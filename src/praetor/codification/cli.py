"""Operator CLI for empirical org-config sweep."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from praetor.codification.report import render_sweep_report_markdown
from praetor.codification.sweep import (
    render_proposed_org_config_yaml,
    run_org_config_sweep,
)
from praetor.correlation import load_fixture_events

SWEEP_LIMITATIONS_EPILOG = """\
Sweep output is review-only and cannot be activated without SOC-lead promotion.

The sweep does not infer:
  - never-contain exclusions (placeholder targets only)
  - subnet membership (UNOBSERVED-REQUIRES-HUMAN-REVIEW sentinel)
  - containment policy statute (development defaults copied verbatim)

Operators must hand-author those sections before activation preflight can pass.
"""


class SweepInputError(Exception):
    """Invalid operator inputs for org-config sweep."""


def load_telemetry_events(path: Path) -> list[dict[str, Any]]:
    """Load a JSON telemetry fixture into a flat event list."""
    if not path.is_file():
        msg = f"telemetry file not found: {path}"
        raise SweepInputError(msg)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON in {path}: {exc}"
        raise SweepInputError(msg) from exc
    try:
        return load_fixture_events(payload)
    except (TypeError, ValueError) as exc:
        msg = f"invalid telemetry fixture in {path}: {exc}"
        raise SweepInputError(msg) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an empirical org-config sweep from normalized Windows telemetry "
            "and write proposed review artifacts."
        ),
        epilog=SWEEP_LIMITATIONS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--org-id",
        required=True,
        help="Organization identifier for proposed version_metadata.org_id",
    )
    parser.add_argument(
        "--sysmon",
        type=Path,
        default=None,
        help="JSON file with Sysmon telemetry (fixture envelope or event list)",
    )
    parser.add_argument(
        "--security",
        type=Path,
        default=None,
        help="JSON file with Windows Security telemetry (fixture envelope or list)",
    )
    parser.add_argument(
        "--output-yaml",
        type=Path,
        required=True,
        help="Path to write proposed org-config YAML artifact",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        required=True,
        help="Path to write markdown sweep coverage/risk report",
    )
    parser.add_argument(
        "--config-version",
        default="sweep-proposed-0.1.0",
        help="Proposed config_version string (default: sweep-proposed-0.1.0)",
    )
    return parser.parse_args(argv)


def run_sweep_cli(
    *,
    org_id: str,
    sysmon_path: Path | None,
    security_path: Path | None,
    output_yaml: Path,
    output_report: Path,
    config_version: str = "sweep-proposed-0.1.0",
) -> None:
    """Execute sweep and write proposed YAML plus markdown report."""
    normalized_org_id = org_id.strip()
    if not normalized_org_id:
        msg = "--org-id must be a non-empty string"
        raise SweepInputError(msg)

    sysmon_events = load_telemetry_events(sysmon_path) if sysmon_path else []
    security_events = load_telemetry_events(security_path) if security_path else []

    result = run_org_config_sweep(
        sysmon_events=sysmon_events,
        security_events=security_events,
        org_id=normalized_org_id,
        config_version=config_version,
    )

    yaml_text = render_proposed_org_config_yaml(result.proposed_config)
    report_text = render_sweep_report_markdown(result.report)

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_yaml.write_text(yaml_text, encoding="utf-8")
    output_report.write_text(report_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        run_sweep_cli(
            org_id=args.org_id,
            sysmon_path=args.sysmon,
            security_path=args.security,
            output_yaml=args.output_yaml,
            output_report=args.output_report,
            config_version=args.config_version,
        )
    except SweepInputError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


__all__ = [
    "SWEEP_LIMITATIONS_EPILOG",
    "SweepInputError",
    "load_telemetry_events",
    "main",
    "parse_args",
    "run_sweep_cli",
]
