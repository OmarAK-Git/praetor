#!/usr/bin/env python3
"""Batch-promote all pending proposals into the playbook in chronological order.

Use this when multiple proposals were synthesised from the same baseline
(all consolidated before any were approved). Each proposal's full-playbook
snapshot is NOT applied verbatim; instead only its delta is extracted:

  • new entries  --entries whose source==slug and sha==sha[:7]
  • their supersedes --existing entries they mark as superseded

Deltas are applied in chronological order against the live playbook. IDs are
re-allocated when a proposal assigns an ID that is already occupied by a
different entry (collision from two synths running off the same baseline).

A single git commit is made at the end (--no-commit to skip).

Usage:
    batch_approve.py               # promote all pending proposals
    batch_approve.py --no-commit   # promote but don't git-commit
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import dream_lib as dl

PROMOTE_MARKER = "[dream-promote]"
COMPLETION_RE = re.compile(r"^<!-- dream:proposal-complete\s+(?P<attrs>.*?)\s*-->\s*$")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pending_proposals() -> list[Path]:
    """All non-temp pending proposals, sorted chronologically (oldest first)."""
    return sorted(
        p for p in dl.proposals_dir().glob("*.md")
        if not p.name.startswith(".tmp-")
    )


def _marker_attrs(proposal_text: str) -> dict[str, str]:
    for line in proposal_text.splitlines():
        m = COMPLETION_RE.match(line)
        if m:
            return dl.parse_attrs(m.group("attrs"))
    return {}


def _remap_bullet_id(text: str, old_id: str, new_id: str) -> str:
    """Replace **OLD** at the opening bullet of entry text only."""
    pattern = re.compile(rf"^(-\s*\*\*){re.escape(old_id)}(\*\*)", re.MULTILINE)
    return pattern.sub(rf"\g<1>{new_id}\2", text, count=1)


# ---------------------------------------------------------------------------
# Delta extraction
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Delta:
    slug: str
    sha: str
    proposal: Path
    # entries whose source==slug sha==sha[:7] in the proposal (with full text)
    new_entries: list[dl.Entry]
    # target_id -> original superseding entry id (before any remap)
    superseded_map: dict[str, str]
    # populated by apply_delta: original_id -> final_id (only differs on collision)
    id_remap: dict[str, str] = dataclasses.field(default_factory=dict)


def extract_delta(proposal: Path) -> Delta:
    text = dl.read_text(proposal)
    attrs = _marker_attrs(text)
    if not attrs:
        raise ValueError(f"proposal missing completion marker: {proposal.name}")

    slug = attrs["slug"]
    sha = attrs["sha"]
    short = sha[:7]

    # parse_playbook gives us Entry objects with their full .text fields
    pb = dl.parse_playbook(text)
    all_entries = pb.all_entries()

    new_entries = [e for e in all_entries if e.source == slug and e.sha == short]
    new_orig_ids = {e.id for e in new_entries}

    # Which existing entries does this delta supersede?
    superseded_map = {
        e.id: e.superseded_by          # target → superseder's original id
        for e in all_entries
        if e.status == "superseded" and e.superseded_by in new_orig_ids
    }

    return Delta(
        slug=slug, sha=sha, proposal=proposal,
        new_entries=new_entries, superseded_map=superseded_map,
    )


# ---------------------------------------------------------------------------
# Delta application
# ---------------------------------------------------------------------------

def apply_delta(
    pb: dl.Playbook,
    delta: Delta,
) -> tuple[list[str], list[str], list[str]]:
    """Mutate pb in-place. Returns (added_ids, superseded_ids, warnings)."""
    by_id = {e.id: e for e in pb.all_entries()}
    counters = {prefix: dl.max_number(pb, prefix) for _, prefix in dl.SECTIONS}
    added: list[str] = []
    superseded: list[str] = []
    warnings: list[str] = []
    id_remap: dict[str, str] = {}
    skip_indices: set[int] = set()

    # Pass 1 --determine final IDs, handle collisions
    for i, entry in enumerate(delta.new_entries):
        old = entry.id
        if old in by_id:
            existing = by_id[old]
            if existing.source == entry.source and existing.sha == entry.sha:
                # True duplicate (same provenance already in playbook) --skip
                warnings.append(
                    f"skipped duplicate {old} ({entry.source}@{entry.sha}) "
                    f"already in playbook"
                )
                id_remap[old] = old
                skip_indices.add(i)
                continue
            # Collision: same ID, different content → re-allocate
            prefix = entry.prefix
            counters[prefix] += 1
            new_id = f"{prefix}-{counters[prefix]:04d}"
            warnings.append(
                f"re-allocated {old} -> {new_id} "
                f"(collides with existing {existing.source}@{existing.sha})"
            )
            entry.text = _remap_bullet_id(entry.text, old, new_id)
            id_remap[old] = new_id
            entry.id = new_id
        else:
            id_remap[old] = old
            # Keep counter at least as high as the allocated number
            p, n = entry.prefix, entry.number
            if n > counters.get(p, 0):
                counters[p] = n

    delta.id_remap = id_remap

    # Pass 2 --append new entries (skip duplicates and entries with no section)
    for i, entry in enumerate(delta.new_entries):
        if i in skip_indices:
            continue
        try:
            section = pb.section(entry.section)
        except KeyError:
            warnings.append(
                f"unknown section {entry.section!r} for {entry.id} --skipping"
            )
            continue
        # Entries come from the proposal marked superseded/active; force active
        entry.status = "active"
        entry.superseded_by = None
        section.entries.append(entry)
        by_id[entry.id] = entry
        added.append(entry.id)

    # Pass 3 --apply supersedes, using the remapped superseder IDs
    for target_id, orig_superseder in delta.superseded_map.items():
        actual_superseder = id_remap.get(orig_superseder, orig_superseder)
        # If the superseder itself was a duplicate-skip, orig_superseder == its old id
        # and id_remap[orig_superseder] == orig_superseder, which IS in by_id already.
        # That's fine --the supersede still makes semantic sense.
        if actual_superseder not in by_id and orig_superseder not in by_id:
            warnings.append(
                f"superseder {orig_superseder} (->{actual_superseder}) "
                f"not found in playbook -- skipping supersede of {target_id}"
            )
            continue
        target = by_id.get(target_id)
        if target is None:
            warnings.append(
                f"supersede target {target_id} not in playbook --skipping"
            )
            continue
        if target.status == "superseded":
            warnings.append(
                f"supersede target {target_id} already superseded "
                f"(by {target.superseded_by}) --skipping"
            )
            continue
        target.status = "superseded"
        target.superseded_by = actual_superseder
        if "_(superseded by" not in target.text:
            target.text = target.text.rstrip() + \
                f"  _(superseded by {actual_superseder})_"
        superseded.append(target_id)

    return added, superseded, warnings


# ---------------------------------------------------------------------------
# Queue / git helpers (mirrors approve.py)
# ---------------------------------------------------------------------------

def _clear_queue_entry(slug: str, sha: str) -> list[str]:
    short = sha[:7]
    removed: list[str] = []
    for qf in dl.queue_dir().glob("*.json"):
        try:
            data = json.loads(qf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (data.get("slug") == slug
                and str(data.get("sha", "")).startswith(short)):
            qf.unlink()
            removed.append(qf.name)
    return removed


def _git_commit(paths: list[str], message: str) -> None:
    subprocess.run(["git", "add", "--", *paths], check=True)
    subprocess.run(["git", "commit", "--no-verify", "-m", message], check=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Batch-promote all pending proposals into the playbook."
    )
    ap.add_argument("--no-commit", action="store_true")
    args = ap.parse_args(argv)

    proposals = _pending_proposals()
    if not proposals:
        print("no pending proposals to approve")
        return 0

    print(f"batch-approving {len(proposals)} proposal(s):")
    for p in proposals:
        print(f"  {p.name}")
    print()

    playbook_path = dl.playbook_path()
    pb = dl.parse_playbook(dl.read_text(playbook_path))
    running_text = dl.render_playbook(pb)

    # --- Pass 1: process all deltas in-memory, collect everything to write ---
    # Nothing touches disk until this loop finishes cleanly.

    @dataclasses.dataclass
    class _PendingWrite:
        delta: Delta
        added: list[str]
        superseded_ids: list[str]
        warnings: list[str]
        nontrivial_remap: dict[str, str]
        prev_hash: str
        new_hash: str

    pending: list[_PendingWrite] = []

    for proposal in proposals:
        proposal_text = dl.read_text(proposal)
        if not any(
            ln.startswith(dl.COMPLETION_PREFIX)
            for ln in proposal_text.splitlines()
        ):
            print(f"SKIP {proposal.name}: missing completion marker", file=sys.stderr)
            continue

        try:
            delta = extract_delta(proposal)
        except Exception as exc:
            print(f"ERROR extracting delta from {proposal.name}: {exc}",
                  file=sys.stderr)
            return 1

        prev_hash = _sha256(running_text)
        added, superseded_ids, warnings = apply_delta(pb, delta)
        running_text = dl.render_playbook(pb)
        new_hash = _sha256(running_text)

        nontrivial_remap = {k: v for k, v in delta.id_remap.items() if k != v}

        print(f"{delta.slug} @{delta.sha[:7]}:")
        print(f"  +{len(added)} added: {added or '(none)'}")
        print(f"  {len(superseded_ids)} superseded: {superseded_ids or '(none)'}")
        if nontrivial_remap:
            remap_str = ", ".join(f"{k}->{v}" for k, v in nontrivial_remap.items())
            print(f"  id_remap: {remap_str}")
        for w in warnings:
            print(f"  warning: {w}")
        print()

        pending.append(_PendingWrite(
            delta=delta, added=added, superseded_ids=superseded_ids,
            warnings=warnings, nontrivial_remap=nontrivial_remap,
            prev_hash=prev_hash, new_hash=new_hash,
        ))

    if not pending:
        print("nothing to promote (all proposals skipped)")
        return 0

    # --- Pass 2: write everything to disk ---
    # Order: playbook -> digest -> ledger -> queue clear -> archive proposals
    # The playbook is the authoritative record; the rest are bookkeeping.

    final_body = dl.render_playbook(pb).rstrip() + "\n"
    dl.atomic_write(playbook_path, final_body)
    digest_file = dl.digest_path()
    dl.atomic_write(digest_file, dl.render_digest_text(pb))
    print(f"playbook updated: {playbook_path.relative_to(dl.repo_root())}")

    dl.ledger_dir().mkdir(parents=True, exist_ok=True)
    dl.approved_dir().mkdir(parents=True, exist_ok=True)

    ledger_files: list[Path] = []
    archived: list[Path] = []
    approved_slugs: list[str] = []

    for pw in pending:
        d = pw.delta
        ts = dl.now_stamp()
        record: dict[str, Any] = {
            "ts": ts,
            "slug": d.slug,
            "sha": d.sha,
            "proposal": d.proposal.name,
            "added_ids": pw.added,
            "superseded_ids": pw.superseded_ids,
            "id_remap": pw.nontrivial_remap,
            "prev_playbook_sha256": pw.prev_hash,
            "new_playbook_sha256": pw.new_hash,
        }
        # Include sha[:7] in filename to prevent collision when two proposals
        # share the same slug (e.g., two V2-003 commits).
        lf = dl.ledger_dir() / f"{ts}-{d.slug}-{d.sha[:7]}.json"
        dl.atomic_write(lf, json.dumps(record, indent=2) + "\n")
        ledger_files.append(lf)

        _clear_queue_entry(d.slug, d.sha)

        arch = dl.approved_dir() / d.proposal.name
        d.proposal.rename(arch)
        archived.append(arch)
        approved_slugs.append(d.slug)

    if args.no_commit:
        print("(--no-commit) review and commit manually")
        return 0

    paths = (
        [
            str(playbook_path.relative_to(dl.repo_root())).replace("\\", "/"),
            str(digest_file.relative_to(dl.repo_root())).replace("\\", "/"),
        ]
        + [str(lf.relative_to(dl.repo_root())).replace("\\", "/")
           for lf in ledger_files]
        + [str(a.relative_to(dl.repo_root())).replace("\\", "/")
           for a in archived]
        + [".workflow/_dream/queue"]
    )
    slug_label = "+".join(dict.fromkeys(approved_slugs))  # deduped, ordered
    message = f"dream: batch-promote {slug_label} {PROMOTE_MARKER}"
    _git_commit(paths, message)
    print(f"committed: {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
