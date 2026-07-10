#!/usr/bin/env python3
"""Acceptance test for the compaction pass.

Builds a synthetic playbook that re-activates the three V2-003 ground-truth
near-duplicate pairs (currently superseded in the real playbook) and runs the
compaction model against it. Passes iff compaction proposes all three supersessions,
including the cross-section PE-0032 / AG-0088 pair.

Usage:
    python .workflow/_dream/bin/test_compaction.py
    python .workflow/_dream/bin/test_compaction.py --model sonnet
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import dream_lib as dl
from compaction import COMPACTION_SCHEMA, _build_compaction_prompt

DEFAULT_MODEL = os.environ.get("DREAM_MODEL", "haiku")

# The three V2-003 near-duplicate pairs, resolved chronologically.
# For the test we re-activate the superseded member of each pair.
GROUND_TRUTH_PAIRS = [
    ("AG-0087", "AG-0090"),   # same section: NeverContainSnapshot capture timing
    ("PE-0032", "AG-0088"),   # CROSS-SECTION: expired-directive residue (PE -> AG)
    ("AG-0089", "AG-0091"),   # same section: orphan-directive reconciliation
]


def _make_synthetic_playbook() -> str:
    """Return a playbook text with superseded ground-truth entries re-activated.

    We clone the real playbook, flip the three superseded entries back to active,
    and remove their superseded-by markers so the compaction sees them as live
    near-duplicates to find.
    """
    pb = dl.parse_playbook(dl.read_text(dl.playbook_path()))
    by_id = {e.id: e for e in pb.all_entries()}

    for sup_id, _can_id in GROUND_TRUTH_PAIRS:
        e = by_id.get(sup_id)
        if e is None:
            raise ValueError(f"ground-truth entry {sup_id} not found in playbook")
        e.status = "active"
        e.superseded_by = None
        # Strip the "(superseded by ...)" annotation from the bullet text
        import re
        e.text = re.sub(r"\s*_\(superseded by [^)]+\)_", "", e.text).rstrip()

    return dl.render_playbook(pb)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Verify compaction catches all V2-003 ground-truth pairs."
    )
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    print("building synthetic playbook with V2-003 pairs re-activated ...")
    synthetic_text = _make_synthetic_playbook()

    # Verify we re-activated them correctly
    pb_check = dl.parse_playbook(synthetic_text)
    by_id = {e.id: e for e in pb_check.all_entries()}
    for sup_id, can_id in GROUND_TRUTH_PAIRS:
        se = by_id[sup_id]
        ce = by_id[can_id]
        assert se.status == "active", f"{sup_id} should be active in synthetic playbook"
        assert ce.status == "active", f"{can_id} should be active in synthetic playbook"

    print(f"running compaction scan with model={args.model} ...")
    prompt = _build_compaction_prompt(synthetic_text)
    system_prompt = dl.read_text(dl.prompts_dir() / "compaction.system.md")
    data, cost = dl.run_claude_json(
        system_prompt=system_prompt,
        user_prompt=prompt,
        schema_json=json.dumps(COMPACTION_SCHEMA),
        model=args.model,
    )
    print(f"  cost: ${cost:.4f}")

    proposed = {
        c["superseded_id"]: c["canonical_id"]
        for c in data.get("compactions", [])
    }
    if args.verbose:
        for sup, can in proposed.items():
            print(f"  proposed: {sup} -> {can}")

    # Check all three ground-truth pairs were found
    failures: list[str] = []
    for sup_id, can_id in GROUND_TRUTH_PAIRS:
        if sup_id not in proposed:
            failures.append(f"MISS: {sup_id} not proposed as superseded")
        elif proposed[sup_id] != can_id:
            failures.append(
                f"WRONG_CANONICAL: {sup_id} -> {proposed[sup_id]} (expected {can_id})"
            )
        else:
            cross = by_id[sup_id].section != by_id[can_id].section
            print(
                f"  PASS: {sup_id} -> {can_id}"
                f"{'  (cross-section!)' if cross else ''}"
            )

    # Report any extra proposed supersessions (false positives are a review risk)
    expected_sups = {p[0] for p in GROUND_TRUTH_PAIRS}
    extras = [s for s in proposed if s not in expected_sups]
    if extras:
        print(f"  NOTE: {len(extras)} extra proposal(s) (review carefully): {extras}")

    if failures:
        print(f"\nFAIL: {len(failures)} ground-truth pair(s) not caught:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"\nPASS: all {len(GROUND_TRUTH_PAIRS)} ground-truth pairs caught"
          f" (including cross-section PE-0032/AG-0088)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
