#!/usr/bin/env python3
"""Consolidate one queued slug into a proposal (the "output store").

Flow:
  1. Pick a queue entry (oldest, or --queue-file / --slug+--sha).
  2. Read the CURRENT playbook (input store; opened read-only, never mutated here).
  3. Read the slug's reliably-present .workflow files.
  4. Ask the Claude CLI (headless, tool-less, json-schema'd) for ADDITIVE
     candidates only: new entries + optional supersede pointers. The model never
     sees a "rewrite the playbook" affordance.
  5. ASSEMBLE the proposal in code (dream_lib.apply_candidates): every existing
     entry copied verbatim (markers preserved; superseded ones get
     status/superseded-by flipped), new entries appended with code-stamped
     provenance (slug + sha). The model physically cannot drop an entry.
  6. Write proposals/<ts>-<slug>.md ATOMICALLY with a completion marker.
  7. Self-run the conservation check and report (the standalone checker remains
     the authoritative gate, re-run by approve.py).

The default model is opus (overridable via $DREAM_MODEL or --model).
For backfilling many already-committed slugs into one proposal, see backfill.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import conservation_check
import dream_lib as dl

DEFAULT_MODEL = os.environ.get("DREAM_MODEL", "opus")


def pick_queue_entry(
    queue_file: Path | None, slug: str | None, sha: str | None
) -> tuple[str, str, Path | None]:
    if slug and sha:
        return slug, sha, None
    if queue_file is not None:
        data = json.loads(queue_file.read_text(encoding="utf-8"))
        return data["slug"], data["sha"], queue_file
    files = sorted(dl.queue_dir().glob("*.json"))
    if not files:
        raise SystemExit("queue is empty; nothing to consolidate")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    return data["slug"], data["sha"], files[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Consolidate a queued slug into a proposal."
    )
    ap.add_argument("--queue-file", type=Path, default=None)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--sha", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="proceed even if the slug's state.json status is not 'complete'",
    )
    args = ap.parse_args(argv)

    slug, sha, _qfile = pick_queue_entry(args.queue_file, args.slug, args.sha)

    status = dl.slug_status(slug)
    if status != "complete" and not args.allow_incomplete:
        print(
            f"refusing: {slug} status={status!r} (not 'complete'); "
            f"pass --allow-incomplete to override",
            file=sys.stderr,
        )
        return 2

    dl.proposals_dir().mkdir(parents=True, exist_ok=True)
    dl.clean_stale_temps(dl.proposals_dir())

    playbook_text = dl.read_text(dl.playbook_path())
    pb = dl.parse_playbook(playbook_text)
    bundle = dl.read_slug_bundle(slug)
    system_prompt = dl.read_text(dl.prompts_dir() / "consolidate.system.md")
    user_prompt = dl.build_synthesis_prompt(slug, sha, playbook_text, bundle)

    print(f"synthesizing {slug} @{sha[:7]} with model={args.model} ...")
    data, cost = dl.run_claude_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema_json=json.dumps(dl.OUTPUT_SCHEMA),
        model=args.model,
    )
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        print("error: model returned no candidates array", file=sys.stderr)
        return 2

    added, superseded, warnings = dl.apply_candidates(pb, slug, sha, candidates)
    marker = dl.completion_marker(
        slug=slug,
        sha=sha[:7],
        ts=dl.now_stamp(),
        model=args.model,
        added=len(added),
        superseded=len(superseded),
    )
    proposal_text = dl.render_playbook(pb).rstrip() + "\n\n" + marker + "\n"
    out_path = dl.proposals_dir() / f"{dl.now_stamp()}-{slug}.md"
    dl.atomic_write(out_path, proposal_text)

    print(f"proposal written: {out_path.relative_to(dl.repo_root())}")
    print(f"  added {len(added)} entr(ies): {added or '(none)'}")
    print(f"  superseded {len(superseded)}: {superseded or '(none)'}")
    print(f"  cost: ${cost:.4f}")
    if data.get("notes"):
        print(f"  model notes: {str(data['notes']).strip()[:300]}")
    for w in warnings:
        print(f"  warning: {w}")

    violations = conservation_check.check(playbook_text, proposal_text)
    if violations:
        print("SELF-CHECK FAILED (this is a bug in assembly):", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("self conservation-check: PASS")
    print("Review it, then run: python .workflow/_dream/bin/approve.py --proposal "
          f"{out_path.relative_to(dl.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
