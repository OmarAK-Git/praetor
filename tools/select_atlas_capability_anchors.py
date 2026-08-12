"""Select ATLASv2 capability-spike anchors from attack-day Security XML + GT.

Malicious: distinct attack-action GT times (not every GT row).
Benign: non-GT 4624s spread across each file's full time range.

Prints YAML-ready candidate rows; does not write the manifest.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "atlasv2" / "data" / "attack"

RE_EID = re.compile(rb"<EventID(?:\s[^>]*)?>(\d+)</EventID>", re.I)
RE_RID = re.compile(rb"<EventRecordID>(\d+)</EventRecordID>", re.I)
RE_TIME = re.compile(rb"SystemTime=['\"]([^'\"]+)['\"]")
RE_DATA = re.compile(rb"<Data Name=['\"]([^'\"]+)['\"]>([^<]*)</Data>", re.I)
CHUNK = 16 * 1024 * 1024
OVERLAP = 8192

# Distinct-action markers (lowercase substrings in ProcessName/ObjectName/etc.).
ACTION_MARKERS: tuple[tuple[str, str], ...] = (
    ("payload_exe", r"payload\.exe"),
    ("portal_index", r"index\.html"),
    ("meterpreter", r"meterpreter"),
    ("0xevil", r"0xevil"),
    ("mei_payload_drop", r"_mei\d+"),  # only keep if also near payload — filtered later
    ("powershell", r"powershell\.exe"),
    ("cmd_exe", r"\\cmd\.exe"),
    ("net_exe", r"\\net\.exe"),
    ("rundll", r"rundll32\.exe"),
    ("wscript", r"wscript\.exe"),
    ("cscript", r"cscript\.exe"),
    ("mshta", r"mshta\.exe"),
    ("certutil", r"certutil\.exe"),
    ("bitsadmin", r"bitsadmin\.exe"),
)

MIN_MAL_GAP = timedelta(minutes=5)
MIN_BEN_GAP = timedelta(minutes=10)


@dataclass
class EventHit:
    rid: str
    eid: str
    ts: datetime
    proc: str
    obj: str
    user: str
    in_gt: bool
    action: str | None


def load_gt_ids(path: Path) -> set[str]:
    return {
        tok
        for tok in re.split(r"[\s,]+", path.read_text(encoding="utf-8"))
        if tok.isdigit()
    }


def parse_ts(raw: bytes | None) -> datetime | None:
    if not raw:
        return None
    text = raw.decode("ascii", "ignore").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


# Processes that often appear in GT via entity sweep but are not attack actions.
_NOISE_PROCS = re.compile(
    r"(searchprotocolhost|spoolsv|tpautoconnect|repmgr|wmiprvse|svchost)\\?",
    re.I,
)


def classify_action(proc: str, obj: str) -> str | None:
    blob = f"{proc} {obj}".lower().replace("/", "\\")
    proc_l = proc.lower().replace("/", "\\")
    # Prefer concrete attack artifacts over generic shells.
    for name, pattern in ACTION_MARKERS:
        if name == "mei_payload_drop":
            continue
        if not re.search(pattern, blob, re.I):
            continue
        if name == "portal_index" and _NOISE_PROCS.search(proc_l):
            return None
        if name in {"powershell", "cmd_exe"} and _NOISE_PROCS.search(proc_l):
            return None
        if name == "mshta" and "registration\\r" in blob:
            # Common mshta registration noise, not attack payload.
            return None
        return name
    return None


def _nearest_before(pattern: re.Pattern[bytes], buf: bytes, pos: int) -> re.Match[bytes] | None:
    """Last regex match whose end is <= pos (event-local field association)."""
    best: re.Match[bytes] | None = None
    for match in pattern.finditer(buf, max(0, pos - 2500), pos):
        best = match
    return best


def scan_security_xml(
    xml: Path,
    *,
    gt_ids: set[str],
) -> list[EventHit]:
    """Stream XML; keep GT action rows + non-GT benign candidates.

    Non-GT keepers: all 4624s, plus one ordinary event per ``MIN_BEN_GAP``
    bucket so benign anchors can span the full file when 4624s cluster.
    """
    hits: list[EventHit] = []
    seen_rids: set[str] = set()
    filler_buckets: set[int] = set()
    with xml.open("rb") as handle:
        head = handle.read(3)
        carry = b"" if head == b"\xef\xbb\xbf" else head
        while True:
            chunk = handle.read(CHUNK)
            if not chunk and not carry:
                break
            buf = carry + chunk
            for match in RE_RID.finditer(buf):
                rid = match.group(1).decode()
                if rid in seen_rids:
                    continue
                eid_m = _nearest_before(RE_EID, buf, match.start())
                eid = eid_m.group(1).decode() if eid_m else "?"
                in_gt = rid in gt_ids
                ts_m = _nearest_before(RE_TIME, buf, match.start())
                # TimeCreated can sit after EventRecordID in some exports.
                if ts_m is None:
                    ts_m = RE_TIME.search(buf, match.start(), match.start() + 800)
                ts = parse_ts(ts_m.group(1) if ts_m else None)
                if ts is None:
                    continue

                keep = False
                if in_gt:
                    keep = True
                elif eid == "4624":
                    keep = True
                else:
                    bucket = int(ts.timestamp() // MIN_BEN_GAP.total_seconds())
                    if bucket not in filler_buckets:
                        filler_buckets.add(bucket)
                        keep = True
                if not keep:
                    seen_rids.add(rid)
                    continue

                end = min(len(buf), match.end() + 4500)
                window = buf[match.start() : end]
                data = {
                    k.decode(): v.decode("utf-8", "ignore")
                    for k, v in RE_DATA.findall(window)
                }
                proc = data.get("ProcessName") or data.get("NewProcessName") or ""
                obj = data.get("ObjectName") or data.get("ShareName") or ""
                user = data.get("TargetUserName") or data.get("SubjectUserName") or ""
                action = classify_action(proc, obj) if in_gt else None
                if in_gt and action is None:
                    # Keep GT process-creates for attack LOLBins / office.
                    if eid == "4688" and proc:
                        name = Path(proc).name.lower()
                        if name in {
                            "winword.exe",
                            "excel.exe",
                            "powerpnt.exe",
                            "payload.exe",
                            "mshta.exe",
                            "powershell.exe",
                            "cmd.exe",
                        }:
                            action = f"proc_{name}"
                        else:
                            seen_rids.add(rid)
                            continue
                    else:
                        seen_rids.add(rid)
                        continue
                seen_rids.add(rid)
                hits.append(
                    EventHit(
                        rid=rid,
                        eid=eid,
                        ts=ts,
                        proc=proc,
                        obj=obj,
                        user=user,
                        in_gt=in_gt,
                        action=action,
                    )
                )
            if not chunk:
                break
            carry = buf[-OVERLAP:]
    return hits


def pick_malicious(hits: list[EventHit]) -> list[EventHit]:
    """One earliest hit per action label, then enforce min gap."""
    by_action: dict[str, EventHit] = {}
    for hit in sorted((h for h in hits if h.in_gt and h.action), key=lambda h: h.ts):
        if hit.action not in by_action:
            by_action[hit.action] = hit
    chosen = sorted(by_action.values(), key=lambda h: h.ts)
    spaced: list[EventHit] = []
    last: datetime | None = None
    for hit in chosen:
        if last is None or hit.ts - last >= MIN_MAL_GAP:
            spaced.append(hit)
            last = hit.ts
    return spaced


def pick_benign(hits: list[EventHit], *, n: int, file_start: datetime, file_end: datetime) -> list[EventHit]:
    """Spread benign times across the file; prefer 4624, else ordinary non-GT."""
    preferred = sorted(
        (h for h in hits if not h.in_gt and h.eid == "4624"),
        key=lambda h: h.ts,
    )
    fillers = sorted(
        (h for h in hits if not h.in_gt and h.eid != "4624"),
        key=lambda h: h.ts,
    )
    if n <= 0 or (not preferred and not fillers):
        return []
    targets = (
        [file_start]
        if n == 1
        else [file_start + (file_end - file_start) * i / (n - 1) for i in range(n)]
    )
    used: list[EventHit] = []
    used_ts: list[datetime] = []

    def _take(pool: list[EventHit], target: datetime) -> EventHit | None:
        best = None
        best_dist = None
        for hit in pool:
            if any(abs(hit.ts - u) < MIN_BEN_GAP for u in used_ts):
                continue
            dist = abs(hit.ts - target)
            if best_dist is None or dist < best_dist:
                best, best_dist = hit, dist
        return best

    for target in targets:
        best = _take(preferred, target) or _take(fillers, target)
        if best is None:
            continue
        used.append(best)
        used_ts.append(best.ts)
    return used


def scenario_paths() -> list[tuple[str, Path, Path]]:
    out: list[tuple[str, Path, Path]] = []
    for host in ("h1", "h2"):
        gt_dir = ATLAS / host / "msft-security" / "groundtruth"
        for gt in sorted(gt_dir.iterdir()):
            host_part, scen = gt.name.split("_", 1)
            xml = gt_dir.parent / f"msft-security-{host_part}-{scen}.xml"
            out.append((gt.name, xml, gt))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-scenario-mal", type=int, default=2)
    parser.add_argument("--target-mal", type=int, default=15)
    parser.add_argument("--target-ben", type=int, default=15)
    parser.add_argument(
        "--scenarios",
        default="",
        help="Comma list like h2_m1,h1_m1 (default: all)",
    )
    args = parser.parse_args()
    allow = {s.strip() for s in args.scenarios.split(",") if s.strip()} or None

    all_mal: list[tuple[str, EventHit]] = []
    all_ben: list[tuple[str, EventHit]] = []

    for name, xml, gt in scenario_paths():
        if allow is not None and name not in allow:
            continue
        if not xml.is_file():
            print(f"# missing xml for {name}")
            continue
        print(f"# scanning {name} ({xml.stat().st_size/1e6:.0f} MB)...", flush=True)
        gt_ids = load_gt_ids(gt)
        hits = scan_security_xml(xml, gt_ids=gt_ids)
        gt_hits = [h for h in hits if h.in_gt]
        times = [h.ts for h in hits]
        if not times:
            print(f"# {name}: no hits")
            continue
        file_start, file_end = min(times), max(times)
        mal = pick_malicious(gt_hits)[: args.per_scenario_mal]
        for hit in mal:
            all_mal.append((name, hit))
            print(
                f"# MAL {name} action={hit.action} eid={hit.eid} "
                f"t={hit.ts.isoformat()} rid={hit.rid} proc={hit.proc[:60]} "
                f"obj={hit.obj[:60]}"
            )
        bens = pick_benign(
            hits,
            n=max(3, args.target_ben // 3),
            file_start=file_start,
            file_end=file_end,
        )
        for hit in bens:
            all_ben.append((name, hit))
            print(
                f"# BEN {name} eid={hit.eid} t={hit.ts.isoformat()} "
                f"rid={hit.rid} user={hit.user}"
            )
        print(
            f"# {name} range={file_start.isoformat()}..{file_end.isoformat()} "
            f"gt_actionable={len(gt_hits)} mal_picked={len(mal)} ben_pool={len(bens)}"
        )

    def _mal_quality(item: tuple[str, EventHit]) -> tuple[int, float]:
        _name, hit = item
        action = hit.action or ""
        rank = {
            "payload_exe": 100,
            "proc_payload.exe": 95,
            "proc_winword.exe": 90,
            "mshta": 80,
            "portal_index": 75,
            "proc_cmd.exe": 40,
            "cmd_exe": 35,
            "powershell": 30,
            "proc_powershell.exe": 30,
        }.get(action, 10)
        # Prefer object paths that name the payload.
        blob = f"{hit.proc} {hit.obj}".lower()
        if "payload.exe" in blob:
            rank += 20
        if "customdestinations" in blob or "temporary internet files" in blob:
            rank -= 40
        # Usable Path B seed floor: payload/office (or payload path), not shell noise.
        if rank < 80 and "payload.exe" not in blob:
            rank = -1
        return (rank, hit.ts.timestamp())

    # Prefer one seed per scenario id, highest quality first, then fill.
    by_scen: dict[str, list[tuple[str, EventHit]]] = defaultdict(list)
    for item in all_mal:
        if _mal_quality(item)[0] < 0:
            continue
        by_scen[item[0].split("_", 1)[1]].append(item)
    selected_mal: list[tuple[str, EventHit]] = []
    for scen in sorted(by_scen):
        best = max(by_scen[scen], key=_mal_quality)
        selected_mal.append(best)
    selected_mal.sort(key=lambda x: x[1].ts)
    if len(selected_mal) > args.target_mal:
        # Keep highest-quality when over target (should be rare at 10 scenarios).
        selected_mal = sorted(selected_mal, key=_mal_quality, reverse=True)[
            : args.target_mal
        ]
        selected_mal.sort(key=lambda x: x[1].ts)
    elif len(selected_mal) < args.target_mal:
        chosen = {id(x) for x in selected_mal}
        extras = sorted(all_mal, key=_mal_quality, reverse=True)
        for item in extras:
            if id(item) in chosen:
                continue
            selected_mal.append(item)
            if len(selected_mal) >= args.target_mal:
                break
        selected_mal.sort(key=lambda x: x[1].ts)

    # Benign: spread globally by sorting and taking evenly spaced
    ben_sorted = sorted(all_ben, key=lambda x: x[1].ts)
    selected_ben: list[tuple[str, EventHit]] = []
    if ben_sorted:
        n = min(args.target_ben, len(ben_sorted))
        if n == 1:
            selected_ben = [ben_sorted[0]]
        else:
            idxs = [round(i * (len(ben_sorted) - 1) / (n - 1)) for i in range(n)]
            selected_ben = [ben_sorted[i] for i in idxs]

    # Balance
    n = min(len(selected_mal), len(selected_ben), args.target_mal, args.target_ben)
    selected_mal = selected_mal[:n]
    selected_ben = selected_ben[:n]

    # Residue = scenarios with no usable Path B seed anywhere (not selection cap).
    all_scen = {"m1", "m2", "m3", "m4", "m5", "m6", "s1", "s2", "s3", "s4"}
    scen_with_any_mal = {
        name.split("_", 1)[1] for name, _ in all_mal
    }
    unchained = sorted(all_scen - scen_with_any_mal)
    selected_scen = {s.split("_", 1)[1] for s, _ in selected_mal}
    print(
        f"\n# summary mal={len(selected_mal)} ben={len(selected_ben)} "
        f"selected_scenarios={sorted(selected_scen)} "
        f"path_b_seeded_scenarios={sorted(scen_with_any_mal)} "
        f"unchained={unchained}"
    )

    print("\ncapture_id: atlasv2-attack-day-2022-07-19")
    print("emulation_steps_total: 10")
    print(f"unchained_steps: {len(unchained)}")
    print("anchors:")
    for i, (name, hit) in enumerate(selected_mal, 1):
        print(f"  - anchor_id: mal-{i:02d}")
        print(f"    anchor_time: {hit.ts.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print("    expected_class: malicious")
        print(
            f"    rationale: >-\n      ATLAS {name} distinct action {hit.action} "
            f"(Security EID {hit.eid} EventRecordID {hit.rid}; "
            f"proc={hit.proc or 'n/a'}; obj={hit.obj or 'n/a'})."
        )
    for i, (name, hit) in enumerate(selected_ben, 1):
        print(f"  - anchor_id: ben-{i:02d}")
        print(f"    anchor_time: {hit.ts.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print("    expected_class: benign")
        print(
            f"    rationale: >-\n      ATLAS {name} non-GT Security EID {hit.eid} "
            f"(EventRecordID {hit.rid}; user={hit.user or 'n/a'}) "
            f"outside groundtruth, spaced across attack-day file range."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
