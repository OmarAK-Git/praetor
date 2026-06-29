#!/usr/bin/env python3
"""Enqueue a completed slug for later consolidation.

This is the ONLY thing the post-commit hook runs. It does no synthesis and adds
no latency beyond a couple of git calls plus a small file append.

Usage:
    enqueue.py --from-head            # derive {slug, sha} from HEAD (hook mode)
    enqueue.py --slug TASK-034 --sha 1d08cfe   # explicit (backfill / dry-run)

A queue entry is a tiny JSON file: {"slug", "sha", "enqueued_at"}.
Enqueue is idempotent per (slug, sha): a duplicate is a no-op.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import dream_lib as dl

PROMOTE_MARKER = "[dream-promote]"
SLUG_PATH_RE = re.compile(r"^\.workflow/(?!_)([^/]+)/")


def _git(args: list[str]) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def head_sha() -> str:
    return _git(["rev-parse", "HEAD"])


def head_message() -> str:
    return _git(["log", "-1", "--pretty=%B"])


def head_changed_paths() -> list[str]:
    raw = _git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
    return [line for line in raw.splitlines() if line.strip()]


def slug_from_paths(paths: list[str]) -> str | None:
    for p in paths:
        m = SLUG_PATH_RE.match(p.replace("\\", "/"))
        if m:
            return m.group(1)
    return None


def derive_from_head() -> tuple[str, str] | None:
    """Return (slug, sha) for HEAD, or None if this commit should be skipped."""
    msg = head_message()
    if PROMOTE_MARKER in msg:
        return None  # loop guard: our own promotion commit
    paths = head_changed_paths()
    dream_prefix = ".workflow/_dream/"
    non_dream = [p for p in paths if not p.replace("\\", "/").startswith(dream_prefix)]
    if not non_dream:
        return None  # commit only touched the dream tool itself
    slug = slug_from_paths(paths)
    if slug is None:
        return None  # no task slug in this commit
    return slug, head_sha()


def enqueue(slug: str, sha: str) -> Path | None:
    short = sha[:7]
    qdir = dl.queue_dir()
    qdir.mkdir(parents=True, exist_ok=True)
    # Idempotency: skip if a queue entry already exists for this (slug, sha).
    for existing in qdir.glob("*.json"):
        try:
            data = json.loads(existing.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("slug") == slug and str(data.get("sha", "")).startswith(short):
            return None
    payload = {
        "slug": slug,
        "sha": sha,
        "enqueued_at": dl.now_stamp(),
    }
    dest = qdir / f"{dl.now_stamp()}-{slug}-{short}.json"
    dl.atomic_write(dest, json.dumps(payload, indent=2) + "\n")
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enqueue a slug for consolidation.")
    ap.add_argument("--from-head", action="store_true", help="derive from HEAD")
    ap.add_argument("--slug", help="explicit slug, e.g. TASK-034")
    ap.add_argument("--sha", help="explicit commit sha")
    args = ap.parse_args(argv)

    if args.from_head:
        derived = derive_from_head()
        if derived is None:
            return 0  # nothing to enqueue; never an error
        slug, sha = derived
    else:
        if not args.slug or not args.sha:
            ap.error("provide --from-head, or both --slug and --sha")
        slug, sha = args.slug, args.sha

    dest = enqueue(slug, sha)
    if dest is None:
        print(f"already queued: {slug} @{sha[:7]}")
    else:
        print(f"enqueued: {dest.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
