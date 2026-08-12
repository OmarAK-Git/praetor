"""Build ATLAS attack-day JSONL capture for capability spike anchors.

Includes Security + Sysmon events in ±pad seconds around every scored/
unresolved anchor. Windows are derived from seed EventRecordID lookup
(host, channel, RID) when possible — not from approximate timestamps.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ATLAS = ROOT / "atlasv2" / "data" / "attack"

from evals.capability.atlas_xml import (  # noqa: E402
    find_event_by_record_id,
    iter_event_blobs,
    parse_event_blob,
)
from evals.capability.corpus import load_anchor_manifest  # noqa: E402

DEFAULT_PAD = 420  # > ±300s correlation window
SCENARIO_RE = re.compile(r"\b(h[12])_([ms]\d+)\b")


def host_computer(host: str) -> str:
    return "WIN-32-H1" if host == "h1" else "WIN-32-H2"


def security_xml(host: str, scenario: str) -> Path:
    return ATLAS / host / "msft-security" / f"msft-security-{host}-{scenario}.xml"


def sysmon_xml(host: str, scenario: str) -> Path:
    return ATLAS / host / "sysmon" / f"sysmon-{host}-{scenario}.xml"


def resolve_anchor_time(
    *,
    host: str,
    scenario: str,
    channel: str | None,
    record_id: str | None,
    fallback: datetime,
) -> datetime:
    """Derive anchor_time from the seed record; fall back to manifest time."""
    if not record_id:
        return fallback
    ch = (channel or "Security").lower()
    path = (
        security_xml(host, scenario)
        if "security" in ch and "sysmon" not in ch
        else sysmon_xml(host, scenario)
    )
    if not path.is_file():
        return fallback
    found = find_event_by_record_id(path, record_id)
    if found is None:
        return fallback
    ts = found["timestamp"]
    assert isinstance(ts, datetime)
    return ts


def windows_for(
    manifest_path: Path, pad: timedelta
) -> dict[tuple[str, str], list[tuple[datetime, datetime]]]:
    manifest = load_anchor_manifest(manifest_path)
    by_file: dict[tuple[str, str], list[tuple[datetime, datetime]]] = defaultdict(
        list
    )
    for anchor in manifest.anchors:
        m = SCENARIO_RE.search(anchor.rationale)
        if not m:
            continue
        host, scen = m.group(1), m.group(2)
        # Prefer Computer-derived host from seed_host_id when present.
        if anchor.seed_host_id == "WIN-32-H1":
            host = "h1"
        elif anchor.seed_host_id == "WIN-32-H2":
            host = "h2"
        center = resolve_anchor_time(
            host=host,
            scenario=scen,
            channel=anchor.seed_channel,
            record_id=anchor.seed_event_record_id,
            fallback=anchor.anchor_time,
        )
        by_file[(host, scen)].append((center - pad, center + pad))
    return by_file


def in_any_window(ts: datetime, windows: list[tuple[datetime, datetime]]) -> bool:
    return any(start <= ts <= end for start, end in windows)


def extract_events(
    xml: Path,
    *,
    channel_default: str,
    windows: list[tuple[datetime, datetime]],
    source_id: str,
    computer_fallback: str,
) -> list[dict]:
    """Extract events whose timestamps fall in any window (Event-blob parse)."""
    if not windows:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for blob in iter_event_blobs(xml):
        parsed = parse_event_blob(blob)
        if parsed is None:
            continue
        rid = str(parsed["EventRecordID"])
        if rid in seen:
            continue
        ts = parsed["timestamp"]
        assert isinstance(ts, datetime)
        if not in_any_window(ts, windows):
            continue
        seen.add(rid)
        computer = str(parsed.get("Computer") or "").strip() or computer_fallback
        channel = str(parsed.get("Channel") or "").strip() or channel_default
        out.append(
            {
                "EventID": int(parsed["EventID"]),
                "EventRecordID": rid,
                "Channel": channel,
                "Computer": computer,
                "UtcTime": ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "EventData": parsed["EventData"],
                # ATLAS per-scenario exports reuse EventRecordID space.
                "SourceScenario": source_id,
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "evals/capability/manifests/atlasv2_attack_day.yaml",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "evals/capability/captures/atlasv2_attack_day.jsonl",
    )
    parser.add_argument("--pad-seconds", type=int, default=DEFAULT_PAD)
    args = parser.parse_args()

    pad = timedelta(seconds=args.pad_seconds)
    by_file = windows_for(args.manifest, pad)
    if not by_file:
        raise SystemExit("no host_scenario tokens found in manifest rationales")

    all_events: list[dict] = []
    for (host, scen), windows in sorted(by_file.items()):
        sec = security_xml(host, scen)
        sysm = sysmon_xml(host, scen)
        computer = host_computer(host)
        print(
            f"{host}_{scen}: {len(windows)} windows -> "
            f"security={'yes' if sec.is_file() else 'MISSING'} "
            f"sysmon={'yes' if sysm.is_file() else 'MISSING'}",
            flush=True,
        )
        source_id = f"{host}_{scen}"
        if sec.is_file():
            ev = extract_events(
                sec,
                channel_default="Security",
                windows=windows,
                source_id=source_id,
                computer_fallback=computer,
            )
            hours = sorted({e["UtcTime"][:13] for e in ev})
            comps = sorted({e.get("Computer") or "" for e in ev})
            print(
                f"  security events={len(ev)} computers={comps} hours={hours}",
                flush=True,
            )
            all_events.extend(ev)
        if sysm.is_file():
            ev = extract_events(
                sysm,
                channel_default="Microsoft-Windows-Sysmon/Operational",
                windows=windows,
                source_id=source_id,
                computer_fallback=computer,
            )
            print(f"  sysmon events={len(ev)}", flush=True)
            all_events.extend(ev)
        elif sec.is_file():
            print("  WARNING: sysmon file missing — Path A will be Security-only")

    all_events.sort(
        key=lambda e: (
            e["UtcTime"],
            str(e.get("Computer") or ""),
            e["Channel"],
            str(e["EventRecordID"]),
            str(e.get("SourceScenario") or ""),
        )
    )
    # EventRecordID is unique only within a scenario export, not per host.
    deduped: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for event in all_events:
        key = (
            str(event.get("SourceScenario") or ""),
            str(event["Channel"]),
            str(event["EventRecordID"]),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(event)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for event in deduped:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    print(f"wrote {len(deduped)} events -> {args.out}")
    channels = defaultdict(int)
    for event in deduped:
        channels[str(event["Channel"])] += 1
    print("channels:", dict(channels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
