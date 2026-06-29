#!/usr/bin/env python3
"""Backfill many already-committed slugs into ONE proposal (the output store).

Where consolidate.py turns one queued slug into one proposal, backfill threads a
single growing playbook through a list of slugs: it synthesizes each slug in its
own isolated, tool-less `claude -p` session (no conversation/repo/CLAUDE.md
context - only a COMPACT playbook digest + that slug's files), folds the candidates
into the in-memory playbook, and after each slug writes a CHECKPOINT proposal.

Safety properties this version adds (after a run that exhausted a Pro window):
  * Per-slug checkpoint: the in-progress proposal is rewritten atomically after
    every slug, so a usage-limit failure or crash never loses completed work.
  * Resume: re-running picks up the checkpoint and skips slugs already represented,
    so you never re-synthesize (and re-pay for) finished slugs.
  * Digest context + --lean: each call ships a marker-free playbook digest and
    (optionally) the 3 highest-signal files per slug - far fewer tokens per call.

Conservation is still enforced in code per slug and re-verified at the end against
the on-disk playbook. It does NOT gate on state.json status (older slugs predate the
flag); a slug whose call fails is skipped (warned), not fatal.

Usage:
  backfill.py --slugs TASK-017,TASK-018,...   # explicit, ordered set (recommended)
  backfill.py --model sonnet --lean            # cheaper bulk pass
  backfill.py                                  # all task slugs not yet in the playbook
Re-run the SAME command after an interruption to resume from the checkpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any

import conservation_check
import dream_lib as dl

DEFAULT_MODEL = os.environ.get("DREAM_MODEL", "opus")
CHECKPOINT_NAME = "backfill-inprogress.md"
_NUM_RE = re.compile(r"\d+")


def natural_key(slug: str) -> str:
    """Sort task-001 < TASK-003 < TASK-028 < TASK-028a < TASK-029."""
    return _NUM_RE.sub(lambda m: m.group().zfill(12), slug.lower())


def provenance_sha(slug: str) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", f".workflow/{slug}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip() or "uncommitted"
    except (subprocess.SubprocessError, OSError):
        return "uncommitted"


def discover_slugs(already: set[str]) -> list[str]:
    root = dl.repo_root() / ".workflow"
    found = [
        p.name
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith("_") and p.name not in already
    ]
    return sorted(found, key=natural_key)


def _strip_completion(text: str) -> str:
    return "\n".join(
        ln for ln in text.splitlines() if not ln.startswith(dl.COMPLETION_PREFIX)
    )


def _write_proposal(pb: dl.Playbook, name: str, model: str, **counts: object) -> str:
    marker = dl.completion_marker(
        slug=("backfill" if "inprogress" not in name else "backfill-inprogress"),
        sha="multiple",
        ts=dl.now_stamp(),
        model=model,
        **counts,
    )
    text = dl.render_playbook(pb).rstrip() + "\n\n" + marker + "\n"
    dl.atomic_write(dl.proposals_dir() / name, text)
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill many slugs into one proposal.")
    ap.add_argument("--slugs", default=None, help="comma-separated, ordered")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--lean", action="store_true", help="send fewer files per slug")
    args = ap.parse_args(argv)

    dl.proposals_dir().mkdir(parents=True, exist_ok=True)
    dl.clean_stale_temps(dl.proposals_dir())

    playbook_text0 = dl.read_text(dl.playbook_path())
    checkpoint = dl.proposals_dir() / CHECKPOINT_NAME
    resuming = checkpoint.exists()
    if resuming:
        pb = dl.parse_playbook(_strip_completion(dl.read_text(checkpoint)))
        print(f"resuming from checkpoint: {checkpoint.name}")
    else:
        pb = dl.parse_playbook(playbook_text0)

    present = {e.source for e in pb.all_entries()}
    if args.slugs:
        requested = [s.strip() for s in args.slugs.split(",") if s.strip()]
    else:
        requested = discover_slugs(present)
    remaining = [s for s in requested if s not in present]
    skipped_present = [s for s in requested if s in present]

    if not remaining:
        if resuming:
            text = _write_proposal(
                pb, f"{dl.now_stamp()}-backfill.md", args.model, sources="resumed"
            )
            checkpoint.unlink()
            print("checkpoint finalized; no remaining slugs to synthesize")
            return 0 if not conservation_check.check(playbook_text0, text) else 1
        print("nothing to backfill (all requested slugs already in the playbook)")
        return 0

    system_prompt = dl.read_text(dl.prompts_dir() / "consolidate.system.md")
    print(
        f"backfilling {len(remaining)} slug(s) with model={args.model} "
        f"(lean={args.lean}): {', '.join(remaining)}"
    )
    if skipped_present:
        print(f"  (already present, skipped: {', '.join(skipped_present)})")

    added_all: list[str] = []
    superseded_all: list[str] = []
    failures: list[str] = []
    total_cost = 0.0

    for i, slug in enumerate(remaining, 1):
        sha = provenance_sha(slug)
        status = dl.slug_status(slug)
        flag = "" if status in ("complete", "completed") else f" [status={status!r}]"
        try:
            bundle = dl.read_slug_bundle(slug, lean=args.lean)
        except FileNotFoundError as exc:
            print(f"  [{i}/{len(remaining)}] {slug}: SKIP ({exc})")
            failures.append(slug)
            continue

        prompt = dl.build_synthesis_prompt(
            slug,
            sha,
            dl.playbook_digest(pb),
            bundle,
            existing_ids=[e.id for e in pb.all_entries()],
        )
        try:
            data, cost = dl.run_claude_json(
                system_prompt=system_prompt,
                user_prompt=prompt,
                schema_json=json.dumps(dl.OUTPUT_SCHEMA),
                model=args.model,
            )
        except (RuntimeError, json.JSONDecodeError, OSError) as exc:
            print(f"  [{i}/{len(remaining)}] {slug}: SKIP (synthesis failed: {exc})")
            failures.append(slug)
            continue

        total_cost += cost
        raw = data.get("candidates", [])
        candidates: list[dict[str, Any]] = raw if isinstance(raw, list) else []
        added, superseded, warnings = dl.apply_candidates(pb, slug, sha, candidates)
        added_all += added
        superseded_all += superseded
        # checkpoint after EVERY slug so a limit/crash never loses work
        _write_proposal(
            pb,
            CHECKPOINT_NAME,
            args.model,
            sources="incremental",
            added=len(added_all),
            superseded=len(superseded_all),
        )
        print(
            f"  [{i}/{len(remaining)}] {slug} @{sha[:7]}{flag}: "
            f"+{len(added)} added, {len(superseded)} superseded "
            f"(${cost:.4f}) [checkpointed]"
        )
        for w in warnings:
            print(f"      warning: {w}")

    out_name = f"{dl.now_stamp()}-backfill.md"
    final_text = _write_proposal(
        pb,
        out_name,
        args.model,
        sources=len(remaining) - len(failures),
        added=len(added_all),
        superseded=len(superseded_all),
    )
    if checkpoint.exists():
        checkpoint.unlink()

    print("")
    print(f"proposal written: .workflow/_dream/proposals/{out_name}")
    print(f"  total added: {len(added_all)}; superseded: {len(superseded_all)}")
    print(f"  total cost: ${total_cost:.4f}")
    if failures:
        print(f"  failed/skipped (re-run to retry): {', '.join(failures)}")

    violations = conservation_check.check(playbook_text0, final_text)
    if violations:
        print("SELF-CHECK FAILED (assembly bug):", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("self conservation-check: PASS")
    print(
        f"Review it, then run: python .workflow/_dream/bin/approve.py "
        f"--proposal .workflow/_dream/proposals/{out_name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
