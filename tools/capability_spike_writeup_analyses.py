"""One-shot write-up analyses from the capability spike JSONL (no re-tune)."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from evals.capability.corpus import load_anchor_manifest
from evals.capability.score import (
    BENIGN,
    MALICIOUS,
    PATH_A,
    PATH_B,
    _is_correct,
    _majority_correct,
    score_path,
)
from evals.capability_spike import (
    _load_observations_jsonl,
    build_anchor_confound_features,
    load_capture_events,
)

ROOT = Path(__file__).resolve().parents[1]


def seed_basename(rationale: str) -> str | None:
    match = re.search(r"image=([^;]+)", rationale)
    if match is None:
        return None
    return Path(match.group(1).strip().replace("\\", "/")).name


def stump_correctness(
    features: dict, feature_name: str
) -> dict[str, bool]:
    rows: list[tuple[str, str, object]] = []
    for aid, (exp, feats) in features.items():
        if exp not in (MALICIOUS, BENIGN):
            continue
        rows.append((aid, exp, feats[feature_name]))
    value_counts: dict[object, dict[str, int]] = defaultdict(
        lambda: {MALICIOUS: 0, BENIGN: 0}
    )
    for _, exp, val in rows:
        value_counts[val][exp] += 1
    out: dict[str, bool] = {}
    for aid, exp, val in rows:
        counts = value_counts[val]
        predicted = (
            MALICIOUS if counts[MALICIOUS] >= counts[BENIGN] else BENIGN
        )
        out[aid] = predicted == exp
    return out


def binom_tail(k: int, n: int) -> float:
    """P(X >= k) for X~Binom(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / (2**n)


def main() -> None:
    obs = _load_observations_jsonl(
        ROOT / "evals/capability/captures/atlasv2_capability_spike_results.jsonl"
    )
    manifest = load_anchor_manifest(
        ROOT / "evals/capability/manifests/atlasv2_attack_day.yaml"
    )
    events = load_capture_events(
        ROOT / "evals/capability/captures/atlasv2_attack_day.jsonl"
    )
    features = build_anchor_confound_features(manifest, events)
    anchors = {a.anchor_id: a for a in manifest.anchors}

    stump_a = stump_correctness(features, "path_a_fact_count")
    stump_b = stump_correctness(features, "path_b_pre_cap_count")

    same_right = sorted(a for a, ok in stump_a.items() if ok and stump_b[a])
    same_wrong = sorted(a for a, ok in stump_a.items() if not ok and not stump_b[a])
    a_only = sorted(a for a, ok in stump_a.items() if ok and not stump_b[a])
    b_only = sorted(a for a, ok in stump_a.items() if stump_b[a] and not ok)

    print("=== stump identity (path_a_fact_count vs path_b_pre_cap_count) ===")
    print(f"stump_A_right={sum(stump_a.values())}/26 stump_B_right={sum(stump_b.values())}/26")
    print(f"same_right n={len(same_right)} {same_right}")
    print(f"same_wrong n={len(same_wrong)} {same_wrong}")
    print(f"A_only_right n={len(a_only)} {a_only}")
    print(f"B_only_right n={len(b_only)} {b_only}")
    print(f"identical_correctness_sets={stump_a == stump_b}")

    grouped: dict[str, dict[str, list]] = defaultdict(
        lambda: {PATH_A: [], PATH_B: []}
    )
    for o in obs:
        if o.path in (PATH_A, PATH_B):
            grouped[o.anchor_id][o.path].append(o)

    model: dict[str, dict[str, str]] = {PATH_A: {}, PATH_B: {}}
    for path in (PATH_A, PATH_B):
        for aid, paths in grouped.items():
            model[path][aid] = _majority_correct(paths[path])

    print("\n=== 1. Model vs stump 2x2 (anchor-majority vs path-matched stump) ===")
    for path, stump, label in (
        (PATH_A, stump_a, "path_a_fact_count"),
        (PATH_B, stump_b, "path_b_pre_cap_count"),
    ):
        both_r, both_w, m_only, s_only = [], [], [], []
        for aid in sorted(stump):
            m_out = model[path][aid]
            assert m_out != "excluded", (path, aid)
            m_ok = m_out == "right"
            s_ok = stump[aid]
            if m_ok and s_ok:
                both_r.append(aid)
            elif not m_ok and not s_ok:
                both_w.append(aid)
            elif m_ok and not s_ok:
                m_only.append(aid)
            else:
                s_only.append(aid)
        print(f"\npath={path} stump={label}")
        print(f"  both_right                 n={len(both_r):2d}  {both_r}")
        print(f"  both_wrong                 n={len(both_w):2d}  {both_w}")
        print(f"  model_right_stump_wrong    n={len(m_only):2d}  {m_only}")
        print(f"  stump_right_model_wrong    n={len(s_only):2d}  {s_only}")
        print(
            f"  discordant={len(m_only) + len(s_only)} "
            f"(model-only wins {len(m_only)}, stump-only wins {len(s_only)})"
        )

    print("\n=== 2. McNemar Path A vs Path B (anchor-majority, n=26) ===")
    a_r_b_w, a_w_b_r, both_r, both_w = [], [], [], []
    for aid in sorted(grouped):
        a_out, b_out = model[PATH_A][aid], model[PATH_B][aid]
        assert a_out != "excluded" and b_out != "excluded"
        ar, br = a_out == "right", b_out == "right"
        if ar and br:
            both_r.append(aid)
        elif not ar and not br:
            both_w.append(aid)
        elif ar and not br:
            a_r_b_w.append(aid)
        else:
            a_w_b_r.append(aid)
    b_ct, c_ct = len(a_r_b_w), len(a_w_b_r)
    n_disc = b_ct + c_ct
    if n_disc == 0 or b_ct == c_ct:
        p_exact = 1.0
    else:
        p_exact = min(1.0, 2 * binom_tail(max(b_ct, c_ct), n_disc))
    chi2 = ((abs(b_ct - c_ct) - 1) ** 2 / n_disc) if n_disc else 0.0
    p_chi = math.erfc(math.sqrt(chi2 / 2)) if chi2 > 0 else 1.0
    print(f"both_right={len(both_r)} both_wrong={len(both_w)}")
    print(f"A_right_B_wrong b={b_ct} {a_r_b_w}")
    print(f"A_wrong_B_right c={c_ct} {a_w_b_r}")
    print(f"McNemar exact two-sided p={p_exact:.6g} (discordant n={n_disc})")
    print(f"McNemar chi2 continuity-corrected chi2={chi2:.4f} p≈{p_chi:.6g}")

    print("\n=== 3. Named cell-level misses + seed basename ===")

    def report_misses(path: str, expected: str) -> None:
        cells = [
            o
            for o in obs
            if o.path == path
            and o.expected_class == expected
            and o.proposed_disposition is not None
        ]
        bad = [
            o
            for o in cells
            if not _is_correct(expected, str(o.proposed_disposition))
        ]
        print(f"\n{path} expected={expected} miss_cells={len(bad)}/{len(cells)}")
        by_anchor: dict[str, list[str]] = defaultdict(list)
        for o in bad:
            by_anchor[o.anchor_id].append(str(o.proposed_disposition))
        seed_anchor = Counter()
        seed_cell = Counter()
        for aid, disps in sorted(by_anchor.items()):
            img = seed_basename(anchors[aid].rationale)
            seed_anchor[img] += 1
            seed_cell[img] += len(disps)
            print(
                f"  {aid} n_cells={len(disps)} "
                f"disps={dict(Counter(disps))} seed={img}"
            )
        print(f"  by_seed_anchors {dict(seed_anchor)}")
        print(f"  by_seed_cells   {dict(seed_cell)}")

    report_misses(PATH_A, MALICIOUS)
    report_misses(PATH_A, BENIGN)
    report_misses(PATH_B, BENIGN)

    print("\nSeed basename roster (all scored anchors):")
    roster = Counter()
    for a in manifest.anchors:
        if a.expected_class in (MALICIOUS, BENIGN):
            img = seed_basename(a.rationale)
            roster[(a.expected_class, img)] += 1
            print(f"  {a.anchor_id} {a.expected_class} {img}")
    print("roster counts", dict(roster))
    print(
        "benign seed population",
        dict(
            Counter(
                seed_basename(a.rationale)
                for a in manifest.anchors
                if a.expected_class == BENIGN
            )
        ),
    )

    print("\n=== 4. Run-to-run unstable anchors (temperature=1.0, runs=3) ===")
    for path in (PATH_A, PATH_B):
        sc = score_path(obs, path=path)
        print(
            f"path={path} unstable_n={len(sc.unstable_anchors)} "
            f"ids={list(sc.unstable_anchors)}"
        )
        for aid in sc.unstable_anchors:
            cells = sorted(
                (o for o in obs if o.path == path and o.anchor_id == aid),
                key=lambda o: o.run_index,
            )
            disps = [o.proposed_disposition for o in cells]
            print(f"  {aid} dispositions_by_run={disps}")


if __name__ == "__main__":
    main()
