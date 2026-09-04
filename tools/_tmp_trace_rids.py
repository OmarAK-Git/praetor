import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_atlas_capability_capture import extract_events, windows_for

wf = windows_for(
    Path("evals/capability/manifests/atlasv2_attack_day.yaml"),
    timedelta(seconds=420),
)
ev = extract_events(
    Path("atlasv2/data/attack/h2/msft-security/msft-security-h2-m3.xml"),
    channel_default="Security",
    windows=wf[("h2", "m3")],
)
sample = [e for e in ev if e["UtcTime"].startswith("2022-07-19 20:34")][:8]
print("sample n", len(sample), sample[0] if sample else None)
rids = {e["EventRecordID"] for e in sample}
found = []
with Path("evals/capability/captures/atlasv2_attack_day.jsonl").open(
    encoding="utf-8"
) as handle:
    for line in handle:
        event = json.loads(line)
        if event.get("EventRecordID") in rids and event.get("Computer") == "WIN-32-H2":
            found.append((event["EventRecordID"], event["UtcTime"]))
print("found", found)
