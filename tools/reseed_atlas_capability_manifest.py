#!/usr/bin/env python3
"""Reseed ATLAS capability anchors from profile-matched Security 4688s.

Benign seeds are the malicious seed's profile minus maliciousness:
same host set, Security channel, EventID 4688, same SubjectUserSid,
outside GT, user-behavior process allowlist (not CB/Wireshark instrumentation).

4688 process path is NewProcessName only (not ProcessName — that is 4663/4658).
XML is split on </Event> before any field association.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.capability.atlas_xml import iter_event_blobs, parse_event_blob  # noqa: E402

ATLAS = ROOT / "atlasv2" / "data" / "attack"
GT_DIR = ROOT / "atlasv2" / "groundtruth"
DEFAULT_MANIFEST = ROOT / "evals/capability/manifests/atlasv2_attack_day.yaml"

SEED_EVENT_ID = 4688
SEED_CHANNEL = "Security"
# User-context process creates that look like ordinary workstation activity.
ALLOW_PROCESS_SUBSTR = (
    "\\explorer.exe",
    "\\firefox.exe",
    "\\cmd.exe",
    "\\excel.exe",
    "\\wmpnscfg.exe",
    "\\mmc.exe",
    "\\notepad.exe",
    "\\powershell.exe",
    "\\winword.exe",
    "\\chrome.exe",
)
# Testbed instrumentation — not user behavior.
BLOCK_PROCESS_SUBSTR = (
    "\\dumpcap.exe",
    "\\tshark.exe",
    "\\repux.exe",
    "\\cb.exe",
    "\\carbonblack",
    "\\procmon",
)

# Malicious payload process creates (prefer these when present on the scenario).
MAL_PROCESS_SUBSTR = (
    "\\payload.exe",
    "\\rat.exe",
    "\\beacon.exe",
    "\\mimikatz",
)

# Rationales use tokens like ``h1_m1`` / ``h2_s1`` (not a host_scenario= key).
SCENARIO_RE = re.compile(r"\b(h[12])_([ms]\d+)\b")
SID_RE = re.compile(r"^S-1-5-21-")  # domain/user SIDs; exclude LOCAL SYSTEM etc.


@dataclass(frozen=True)
class Hit:
    host: str
    scenario: str
    ts: datetime
    record_id: str
    process: str
    subject_sid: str
    subject_user: str


def security_xml(host: str, scenario: str) -> Path:
    return ATLAS / host / "msft-security" / f"msft-security-{host}-{scenario}.xml"


def process_basename(path: str) -> str:
    return path.replace("/", "\\").rsplit("\\", 1)[-1].lower()


def is_allowed_benign_process(path: str) -> bool:
    low = path.lower().replace("/", "\\")
    if any(b in low for b in BLOCK_PROCESS_SUBSTR):
        return False
    return any(a in low for a in ALLOW_PROCESS_SUBSTR)


def is_mal_payload_process(path: str) -> bool:
    low = path.lower().replace("/", "\\")
    return any(m in low for m in MAL_PROCESS_SUBSTR)


def load_4688_hits(host: str, scenario: str) -> list[Hit]:
    path = security_xml(host, scenario)
    if not path.is_file():
        return []
    hits: list[Hit] = []
    for blob in iter_event_blobs(path):
        parsed = parse_event_blob(blob)
        if parsed is None:
            continue
        if int(parsed["EventID"]) != SEED_EVENT_ID:
            continue
        data = parsed["EventData"]  # type: ignore[assignment]
        # Security 4688 stores the created process in NewProcessName only.
        proc = str(data.get("NewProcessName") or "").strip()
        if not proc:
            continue
        sid = str(data.get("SubjectUserSid") or "").strip()
        user = str(data.get("SubjectUserName") or "").strip()
        hits.append(
            Hit(
                host=host,
                scenario=scenario,
                ts=parsed["timestamp"],  # type: ignore[arg-type]
                record_id=str(parsed["EventRecordID"]),
                process=proc,
                subject_sid=sid,
                subject_user=user,
            )
        )
    return hits


def load_gt_window(host: str, scenario: str) -> tuple[datetime, datetime] | None:
    path = GT_DIR / f"gt_{host}_{scenario}.csv"
    if not path.is_file():
        return None
    times: list[datetime] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
        if not line.strip():
            continue
        raw = line.split(",", 1)[0].strip().strip('"')
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            continue
        times.append(dt)
    if not times:
        return None
    return min(times) - timedelta(minutes=2), max(times) + timedelta(minutes=2)


def in_gt(ts: datetime, window: tuple[datetime, datetime] | None) -> bool:
    if window is None:
        return False
    return window[0] <= ts <= window[1]


def pick_malicious(hits: list[Hit], gt: tuple[datetime, datetime] | None) -> Hit | None:
    in_window = [h for h in hits if in_gt(h.ts, gt)]
    pool = in_window or hits
    payload = [h for h in pool if is_mal_payload_process(h.process)]
    # Prefer user-context payload creates (not SYSTEM / CB).
    user_payload = [h for h in payload if SID_RE.match(h.subject_sid)]
    ranked = user_payload or payload or [
        h for h in pool if SID_RE.match(h.subject_sid)
    ]
    if not ranked:
        ranked = pool
    if not ranked:
        return None
    ranked.sort(key=lambda h: h.ts)
    return ranked[len(ranked) // 2]


def pick_benign(
    hits: list[Hit],
    *,
    subject_sid: str,
    gt: tuple[datetime, datetime] | None,
    used_rids: set[tuple[str, str]],
) -> Hit | None:
    """Same host/channel/EventID/SID as mal, outside GT, user-behavior process."""
    candidates = [
        h
        for h in hits
        if h.subject_sid == subject_sid
        and not in_gt(h.ts, gt)
        and is_allowed_benign_process(h.process)
        and (h.host, h.record_id) not in used_rids
    ]
    if not candidates:
        return None
    # Prefer mixed pre/post relative to GT center when GT exists.
    if gt is not None:
        center = gt[0] + (gt[1] - gt[0]) / 2
        pre = [h for h in candidates if h.ts < center]
        post = [h for h in candidates if h.ts >= center]
        # Alternate preference: pick farthest from center among the larger side.
        side = pre if len(pre) >= len(post) else post
        side = side or candidates
        side.sort(key=lambda h: abs((h.ts - center).total_seconds()), reverse=True)
        return side[0]
    candidates.sort(key=lambda h: h.ts)
    return candidates[len(candidates) // 2]


def fmt_time(ts: datetime) -> str:
    ts = ts.astimezone(UTC)
    return (
        ts.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{ts.microsecond // 1000:03d}Z"
    )


def host_id(host: str) -> str:
    return "WIN-32-H1" if host == "h1" else "WIN-32-H2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    doc = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    anchors = doc["anchors"]
    mal_rows = [a for a in anchors if a.get("expected_class") == "malicious"]
    ben_rows = [a for a in anchors if a.get("expected_class") == "benign"]

    # Cache 4688 hits per (host, scenario).
    cache: dict[tuple[str, str], list[Hit]] = {}
    gt_cache: dict[tuple[str, str], tuple[datetime, datetime] | None] = {}

    def hits_for(host: str, scen: str) -> list[Hit]:
        key = (host, scen)
        if key not in cache:
            cache[key] = load_4688_hits(host, scen)
        return cache[key]

    def gt_for(host: str, scen: str) -> tuple[datetime, datetime] | None:
        key = (host, scen)
        if key not in gt_cache:
            gt_cache[key] = load_gt_window(host, scen)
        return gt_cache[key]

    used: set[tuple[str, str]] = set()
    sid_counts: dict[str, int] = defaultdict(int)
    updates: list[tuple[dict, Hit, str]] = []

    for row in mal_rows:
        m = SCENARIO_RE.search(str(row.get("rationale") or ""))
        if not m:
            print(f"SKIP mal {row['anchor_id']}: no host_scenario token")
            continue
        host, scen = m.group(1), m.group(2)
        # Prefer existing seed RID when still a valid user-context 4688.
        chosen: Hit | None = None
        want_rid = str(row.get("seed_event_record_id") or "").strip()
        if want_rid:
            for hit in hits_for(host, scen):
                if hit.record_id == want_rid and SID_RE.match(hit.subject_sid):
                    chosen = hit
                    break
        if chosen is None:
            chosen = pick_malicious(hits_for(host, scen), gt_for(host, scen))
        if chosen is None:
            print(f"FAIL mal {row['anchor_id']}: no 4688 seed")
            continue
        used.add((chosen.host, chosen.record_id))
        sid_counts[chosen.subject_sid] += 1
        updates.append((row, chosen, "malicious"))
        print(
            f"mal {row['anchor_id']}: {chosen.host}/{scen} rid={chosen.record_id} "
            f"sid={chosen.subject_sid} proc={process_basename(chosen.process)} "
            f"t={fmt_time(chosen.ts)}"
        )

    # Pair benign with malicious by index; match SubjectUserSid from paired mal.
    mal_hits_by_id = {row["anchor_id"]: hit for row, hit, _ in updates}

    for i, row in enumerate(ben_rows):
        m = SCENARIO_RE.search(str(row.get("rationale") or ""))
        if not m:
            print(f"SKIP ben {row['anchor_id']}: no host_scenario token")
            continue
        host, scen = m.group(1), m.group(2)
        pair_sid = None
        if i < len(mal_rows):
            mid = mal_rows[i]["anchor_id"]
            if mid in mal_hits_by_id:
                pair_sid = mal_hits_by_id[mid].subject_sid
        if not pair_sid:
            pair_sid = max(sid_counts, key=sid_counts.get) if sid_counts else ""

        chosen = pick_benign(
            hits_for(host, scen),
            subject_sid=pair_sid,
            gt=gt_for(host, scen),
            used_rids=used,
        )
        if chosen is None:
            print(
                f"FAIL ben {row['anchor_id']}: no profile-matched 4688 "
                f"(sid={pair_sid})"
            )
            continue
        used.add((chosen.host, chosen.record_id))
        updates.append((row, chosen, "benign"))
        print(
            f"ben {row['anchor_id']}: {chosen.host}/{scen} rid={chosen.record_id} "
            f"sid={chosen.subject_sid} proc={process_basename(chosen.process)} "
            f"t={fmt_time(chosen.ts)}"
        )

    n_ok = sum(1 for _, _, kind in updates if kind == "benign")
    print(f"\nbenign seeded: {n_ok}/{len(ben_rows)}")
    print("malicious SubjectUserSid counts:", dict(sid_counts))

    if not args.write:
        print("(dry-run; pass --write to update manifest)")
        return 0 if n_ok == len(ben_rows) else 1

    by_id = {row["anchor_id"]: (hit, kind) for row, hit, kind in updates}
    for i, row in enumerate(anchors):
        aid = row["anchor_id"]
        if aid not in by_id:
            continue
        hit, kind = by_id[aid]
        token = f"{hit.host}_{hit.scenario}"
        if kind == "malicious":
            rationale = (
                f"ATLAS {token} payload stage (Security EID 4688 "
                f"EventRecordID {hit.record_id}; image={hit.process}; "
                f"SubjectUserSid={hit.subject_sid})."
            )
        else:
            rationale = (
                f"ATLAS {token} ordinary user-context process create "
                f"(Security EID 4688 EventRecordID {hit.record_id}; "
                f"image={hit.process}; SubjectUserSid={hit.subject_sid}; "
                f"outside GT; profile-matched to malicious seeds)."
            )
        anchors[i] = {
            "anchor_id": aid,
            "anchor_time": fmt_time(hit.ts),
            "expected_class": row["expected_class"],
            "seed_event_id": SEED_EVENT_ID,
            "seed_channel": SEED_CHANNEL,
            "seed_event_record_id": str(hit.record_id),
            "seed_host_id": host_id(hit.host),
            "seed_subject_sid": hit.subject_sid,
            "rationale": rationale,
        }

    header = (
        "# ATLASv2 attack-day capability spike anchors "
        "(labels frozen before provider calls).\n"
        "# Malicious: user-context Security 4688 payload.exe creates.\n"
        "# Benign: same host/channel/EventID/SubjectUserSid, outside GT, "
        "allowlisted user apps (not CB/Wireshark instrumentation).\n"
        "# Path A uses anchor_time only; seed_* fields are Guard #2 "
        "confound metadata.\n"
    )
    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
    args.manifest.write_text(header + body, encoding="utf-8")
    print(f"wrote {args.manifest}")
    return 0 if n_ok == len(ben_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
