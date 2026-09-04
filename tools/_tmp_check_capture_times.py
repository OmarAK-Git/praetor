import json
from collections import Counter
from pathlib import Path

path = Path("evals/capability/captures/atlasv2_attack_day.jsonl")
utc = Counter()
n = 0
with path.open(encoding="utf-8") as handle:
    for line in handle:
        if "2022-07-19 20:34" not in line:
            continue
        event = json.loads(line)
        if str(event.get("UtcTime", "")).startswith("2022-07-19 20:34"):
            utc[event["UtcTime"][:19]] += 1
            n += 1
print("utc 20:34 n", n, utc.most_common(3))

hour = Counter()
with path.open(encoding="utf-8") as handle:
    for line in handle:
        if "WIN-32-H2" not in line:
            continue
        event = json.loads(line)
        hour[str(event.get("UtcTime", ""))[:13]] += 1
print("h2 hours", sorted(hour.items()))
