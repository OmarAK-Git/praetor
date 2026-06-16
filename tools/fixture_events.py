"""Flatten committed fixture events for Splunk demo / SPL portability tests.

Canonical flatten logic for TASK-033: PowerShell ingest must mirror this module.
See tools/splunk_ingest_demo.ps1 (calls flatten_fixture_event via Python on ingest).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"
DEFAULT_MANIFEST = DEFAULT_FIXTURES_ROOT / "fixture_manifest.yaml"

SOURCE_BY_CHANNEL: dict[str, str] = {
    "Microsoft-Windows-Sysmon/Operational": "WinEventLog:Microsoft-Windows-Sysmon/Operational",
    "Security": "WinEventLog:Security",
}


class UnsupportedFixtureChannelError(ValueError):
    """Raised when a fixture Channel cannot map to a WinEventLog source."""


def source_for_channel(channel: str) -> str:
    try:
        return SOURCE_BY_CHANNEL[channel]
    except KeyError as exc:
        raise UnsupportedFixtureChannelError(
            f"unsupported fixture Channel for Splunk demo ingest: {channel!r}"
        ) from exc


def flatten_fixture_event(event: dict[str, Any]) -> dict[str, Any]:
    """Flatten one fixture event to Splunk-searchable top-level fields."""
    record: dict[str, Any] = {}
    for key in ("@timestamp", "EventID", "Channel", "Computer", "record_id"):
        if key in event:
            record[key] = event[key]

    event_data = event.get("EventData")
    if event_data is not None:
        if not isinstance(event_data, dict):
            record_id = event.get("record_id", "?")
            msg = f"EventData must be an object in fixture event record_id={record_id!r}"
            raise TypeError(msg)
        record.update(event_data)

    if "EventID" in record:
        record["EventCode"] = record["EventID"]

    channel = str(record["Channel"])
    record["source"] = source_for_channel(channel)
    return record


def iter_manifest_fixture_events(
    fixtures_root: Path = DEFAULT_FIXTURES_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> Iterator[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Yield (manifest_rel_path, raw_event, flattened_event) for manifest-listed fixtures."""
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["fixtures"]:
        rel = entry["path"].removeprefix("fixtures/")
        fixture_path = fixtures_root / rel
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        for event in payload.get("events", []):
            yield entry["path"], event, flatten_fixture_event(event)


def manifest_fixture_count(manifest_path: Path = DEFAULT_MANIFEST) -> int:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return len(manifest["fixtures"])


def _cli_flatten_event() -> int:
    import sys

    event = json.loads(sys.stdin.read())
    sys.stdout.write(json.dumps(flatten_fixture_event(event), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "flatten":
        raise SystemExit(_cli_flatten_event())
    print("usage: python -m tools.fixture_events flatten  (read JSON event from stdin)", file=sys.stderr)
    raise SystemExit(2)
