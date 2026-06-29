#!/usr/bin/env python3
"""Promote a reviewed proposal into the playbook. Run by a human, on purpose.

This is the ONLY step that mutates the input store (playbook.md). It:
  1. Re-runs the conservation check (authoritative gate) and refuses on any
     violation or a missing completion marker.
  2. Atomically replaces playbook.md with the proposal's playbook body (the
     completion-marker line is stripped).
  3. Appends an append-only provenance record to ledger/.
  4. Clears the consumed queue entry for (slug, sha).
  5. Archives the proposal to proposals/approved/.
  6. Commits ONLY .workflow/_dream/ paths with --no-verify and a [dream-promote]
     marker (the post-commit hook skips both the marker and _dream-only commits).

Usage:
    approve.py --proposal proposals/<ts>-<slug>.md   # explicit
    approve.py                                        # newest pending proposal
    approve.py --no-commit                            # promote but don't git commit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import conservation_check
import dream_lib as dl

PROMOTE_MARKER = "[dream-promote]"
COMPLETION_RE = re.compile(r"^<!-- dream:proposal-complete\s+(?P<attrs>.*?)\s*-->\s*$")


def newest_pending_proposal() -> Path:
    pending = sorted(
        p for p in dl.proposals_dir().glob("*.md") if not p.name.startswith(".tmp-")
    )
    if not pending:
        raise SystemExit("no pending proposals to approve")
    return pending[-1]


def split_proposal(text: str) -> tuple[str, dict[str, str]]:
    """Return (playbook_body_without_marker, marker_attrs)."""
    lines = text.splitlines()
    attrs: dict[str, str] = {}
    body_lines: list[str] = []
    for line in lines:
        m = COMPLETION_RE.match(line)
        if m:
            attrs = dl.parse_attrs(m.group("attrs"))
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).rstrip() + "\n"
    return body, attrs


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clear_queue_entry(slug: str, sha: str) -> list[str]:
    short = sha[:7]
    removed: list[str] = []
    for qf in dl.queue_dir().glob("*.json"):
        try:
            data = json.loads(qf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("slug") == slug and str(data.get("sha", "")).startswith(short):
            qf.unlink()
            removed.append(qf.name)
    return removed


def git_commit(paths: list[str], message: str) -> None:
    subprocess.run(["git", "add", "--", *paths], check=True)
    subprocess.run(
        ["git", "commit", "--no-verify", "-m", message], check=True
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote a proposal into the playbook.")
    ap.add_argument("--proposal", type=Path, default=None)
    ap.add_argument("--no-commit", action="store_true")
    args = ap.parse_args(argv)

    proposal = args.proposal if args.proposal is not None else newest_pending_proposal()
    if not proposal.exists():
        print(f"error: no such proposal: {proposal}", file=sys.stderr)
        return 2

    playbook_path = dl.playbook_path()
    playbook_text = dl.read_text(playbook_path)
    proposal_text = dl.read_text(proposal)

    # (1) Authoritative gate.
    violations = conservation_check.check(playbook_text, proposal_text)
    if violations:
        print("REFUSING TO PROMOTE: conservation check failed:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    new_body, attrs = split_proposal(proposal_text)
    slug = attrs.get("slug", "unknown")
    sha = attrs.get("sha", "unknown")

    prev_hash = sha256(playbook_text)
    # (2) Atomic promotion of the input store.
    dl.atomic_write(playbook_path, new_body)
    new_hash = sha256(new_body)

    # (2a) Regenerate the compact startup digest from the just-promoted playbook
    # so the cheap always-on view never drifts from the input store.
    digest_file = dl.digest_path()
    dl.atomic_write(digest_file, dl.render_digest_text(dl.parse_playbook(new_body)))

    # diff entry sets for the ledger
    old_markers = dl.parse_markers(playbook_text)
    old_ids = {e.id for e in old_markers}
    old_superseded = {e.id for e in old_markers if e.status == "superseded"}
    new_entries = dl.parse_markers(new_body)
    added = [e.id for e in new_entries if e.id not in old_ids]
    # Only entries THIS promotion newly superseded — not ones already superseded
    # in the prior playbook (those were attributed to the run that did it).
    superseded = [
        e.id
        for e in new_entries
        if e.status == "superseded" and e.id not in old_superseded
    ]

    # (3) Append-only provenance ledger.
    record: dict[str, Any] = {
        "ts": dl.now_stamp(),
        "slug": slug,
        "sha": sha,
        "proposal": proposal.name,
        "added_ids": added,
        "superseded_ids": superseded,
        "prev_playbook_sha256": prev_hash,
        "new_playbook_sha256": new_hash,
    }
    dl.ledger_dir().mkdir(parents=True, exist_ok=True)
    ledger_file = dl.ledger_dir() / f"{record['ts']}-{slug}.json"
    dl.atomic_write(ledger_file, json.dumps(record, indent=2) + "\n")

    # (4) Clear consumed queue entry.
    removed = clear_queue_entry(slug, sha)

    # (5) Archive the proposal.
    dl.approved_dir().mkdir(parents=True, exist_ok=True)
    archived = dl.approved_dir() / proposal.name
    proposal.rename(archived)

    print(
        f"promoted {slug} @{sha}: +{len(added)} entr(ies), "
        f"{len(superseded)} superseded"
    )
    print(f"  ledger: {ledger_file.relative_to(dl.repo_root())}")
    print(f"  archived proposal: {archived.relative_to(dl.repo_root())}")
    print(f"  cleared queue: {removed or '(none)'}")

    # (6) Commit ONLY dream paths, with loop-guard marker + --no-verify.
    if args.no_commit:
        print("  (--no-commit) staged nothing; review and commit manually")
        return 0
    paths = [
        str(playbook_path.relative_to(dl.repo_root())).replace("\\", "/"),
        str(digest_file.relative_to(dl.repo_root())).replace("\\", "/"),
        str(ledger_file.relative_to(dl.repo_root())).replace("\\", "/"),
        str(archived.relative_to(dl.repo_root())).replace("\\", "/"),
        ".workflow/_dream/queue",
    ]
    message = f"dream: promote {slug} @{sha} {PROMOTE_MARKER}"
    git_commit(paths, message)
    print(f"  committed: {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
