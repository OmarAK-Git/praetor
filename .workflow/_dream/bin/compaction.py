#!/usr/bin/env python3
"""Compaction pass: identify near-duplicate entries and propose supersessions.

Unlike consolidate.py (which synthesises from a slug), compaction reads the
full playbook and asks the model to detect near-duplicate entry pairs — entries
that state the same rule with overlapping or identical consequence — and propose
that the weaker one be superseded by the stronger existing one.

No new slug is required. The compaction is its own event with source=compaction
and sha=<HEAD> in the provenance of any entries it modifies.

Output is a standard proposal file consumable by approve.py. Conservation is
enforced by the same conservation_check.py gate. Nothing changes until you run
approve.py.

Acceptance test: point the compaction at the V2-003 duplicate pairs introduced
when two commits for the same slug each fired a dream:
  AG-0087 / AG-0090  (already resolved)
  AG-0088 / PE-0032  (already resolved via cross-section supersede)
  AG-0089 / AG-0091  (already resolved)
Future cross-commit duplication should produce the same pattern; the compaction
should catch it.

Usage:
    python .workflow/_dream/bin/compaction.py
    python .workflow/_dream/bin/compaction.py --model haiku   # cheaper scan
    python .workflow/_dream/bin/compaction.py --dry-run       # print proposal, no file
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import conservation_check
import dream_lib as dl

DEFAULT_MODEL = os.environ.get("DREAM_MODEL", "opus")

# JSON schema for compaction output — the model only identifies supersede pairs;
# it does NOT create new entries. Each pair names an entry to mark superseded
# and the existing entry that becomes its canonical reference.
COMPACTION_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "compactions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "superseded_id": {
                        "type": "string",
                        "description": (
                            "ID of the weaker/redundant entry to mark superseded"
                        ),
                    },
                    "canonical_id": {
                        "type": "string",
                        "description": (
                            "ID of the surviving canonical entry (must already exist)"
                        ),
                    },
                    "rationale": {"type": "string"},
                },
                "required": ["superseded_id", "canonical_id"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["compactions"],
}


def _head_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def apply_compactions(
    pb: dl.Playbook,
    compactions: list[dict],
    sha: str,
) -> tuple[list[str], list[str]]:
    """Mark superseded_id entries as status=superseded pointing at canonical_id.

    Returns (superseded_ids, warnings).
    """
    by_id = {e.id: e for e in pb.all_entries()}
    superseded: list[str] = []
    warnings: list[str] = []

    for comp in compactions:
        sup_id = str(comp.get("superseded_id", "")).strip()
        can_id = str(comp.get("canonical_id", "")).strip()
        if not sup_id or not can_id:
            warnings.append(f"skipped malformed compaction: {comp!r}")
            continue
        if sup_id == can_id:
            warnings.append(f"skipped self-supersede: {sup_id}")
            continue

        sup_entry = by_id.get(sup_id)
        can_entry = by_id.get(can_id)

        if sup_entry is None:
            warnings.append(f"superseded_id {sup_id!r} not found in playbook")
            continue
        if can_entry is None:
            warnings.append(f"canonical_id {can_id!r} not found in playbook")
            continue
        if sup_entry.status == "superseded":
            warnings.append(
                f"{sup_id} already superseded "
                f"(by {sup_entry.superseded_by}) — skipping"
            )
            continue

        sup_entry.status = "superseded"
        sup_entry.superseded_by = can_id
        if "_(superseded by" not in sup_entry.text:
            sup_entry.text = sup_entry.text.rstrip() + f"  _(superseded by {can_id})_"
        superseded.append(sup_id)

    return superseded, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Compact the playbook: detect and propose near-duplicate "
            "supersessions."
        )
    )
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument(
        "--dry-run", action="store_true",
        help="print the proposal to stdout, do not write a file",
    )
    args = ap.parse_args(argv)

    sha = _head_sha()
    short = sha[:7]
    slug = "compaction"

    dl.proposals_dir().mkdir(parents=True, exist_ok=True)
    dl.clean_stale_temps(dl.proposals_dir())

    playbook_text = dl.read_text(dl.playbook_path())
    pb = dl.parse_playbook(playbook_text)

    system_prompt = dl.read_text(dl.prompts_dir() / "compaction.system.md")
    user_prompt = _build_compaction_prompt(playbook_text)

    print(f"running compaction scan with model={args.model} @{short} ...")
    data, cost = dl.run_claude_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema_json=json.dumps(COMPACTION_SCHEMA),
        model=args.model,
    )

    compactions = data.get("compactions", [])
    if not isinstance(compactions, list):
        print("error: model returned no compactions array", file=sys.stderr)
        return 2

    superseded, warnings = apply_compactions(pb, compactions, sha)

    marker = dl.completion_marker(
        slug=slug,
        sha=short,
        ts=dl.now_stamp(),
        model=args.model,
        added=0,
        superseded=len(superseded),
    )
    proposal_text = dl.render_playbook(pb).rstrip() + "\n\n" + marker + "\n"

    print(f"  proposed {len(superseded)} supersession(s): {superseded or '(none)'}")
    print(f"  cost: ${cost:.4f}")
    if data.get("notes"):
        raw_notes = str(data["notes"]).strip()[:300]
        notes = raw_notes.encode("ascii", errors="replace").decode("ascii")
        print(f"  model notes: {notes}")
    for w in warnings:
        print(f"  warning: {w}")

    violations = conservation_check.check(playbook_text, proposal_text)
    if violations:
        print("SELF-CHECK FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("self conservation-check: PASS")

    if args.dry_run:
        sys.stdout.write(proposal_text)
        return 0

    out_path = dl.proposals_dir() / f"{dl.now_stamp()}-{slug}.md"
    dl.atomic_write(out_path, proposal_text)
    print(f"proposal written: {out_path.relative_to(dl.repo_root())}")
    print(
        f"Review it, then run: python .workflow/_dream/bin/approve.py --proposal "
        f"{out_path.relative_to(dl.repo_root())}"
    )
    return 0


def _build_compaction_prompt(playbook_text: str) -> str:
    entries = dl.parse_markers(playbook_text)
    active_ids = [e.id for e in entries if e.status == "active"]
    return (
        "You are running a compaction pass over the Praetor Dream Playbook.\n\n"
        "## Current playbook\n\n"
        f"Active entry IDs you may reference as `canonical_id`: {active_ids}\n\n"
        f"```markdown\n{playbook_text.strip()}\n```\n\n"
        "## Your job\n\n"
        "Identify pairs of entries where one is a near-duplicate, subset, or "
        "restatement of another — where the same rule is stated twice with "
        "overlapping or identical consequence and no unique content in the weaker "
        "entry. For each pair:\n"
        "- `superseded_id`: the weaker/redundant entry to retire\n"
        "- `canonical_id`: the surviving entry that is already in the playbook\n\n"
        "Rules:\n"
        "- Only propose supersessions where one entry adds NOTHING the other lacks.\n"
        "- Do NOT propose if both entries each add something unique.\n"
        "- Do NOT propose for entries already marked superseded.\n"
        "- `canonical_id` must be an existing active entry ID — do NOT invent IDs.\n"
        "- Prefer the entry with more cross-references, more complete text, or "
        "more recent provenance as the canonical.\n"
        "- If no clear near-duplicates exist, return an empty `compactions` array.\n\n"
        "Known test fixtures (V2-003 cross-commit pairs already resolved — verify "
        "your logic would have caught these before approving them):\n"
        "- AG-0087 superseded by AG-0090 (NeverContainSnapshot capture timing)\n"
        "- PE-0032 superseded by AG-0088 (expired-directive audit residue)\n"
        "- AG-0089 superseded by AG-0091 (orphan-directive reconciliation)\n"
        "- PE-0033 superseded by PE-0034 (containment rule enforcement)\n"
        "- PE-0036 superseded by PE-0035 (rule precedence)\n"
    )


if __name__ == "__main__":
    sys.exit(main())
