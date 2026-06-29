#!/usr/bin/env python3
"""Independently verify a proposal conserves the current playbook.

This is the deterministic mitigation for the memory-poisoning / memory-loss risk
of an LLM-shaped write surface. It trusts ONLY entry markers, never prose, and is
fully independent of how the proposal was assembled.

Invariants enforced (any violation => exit 1):
  1. Completion marker present (proposal is finished, not a partial crash artifact).
  2. No duplicate entry IDs in the proposal.
  3. Conservation: every entry ID in the CURRENT playbook still appears in the
     proposal, as one of:
        - retained   (status=active, unchanged), or
        - superseded (status=superseded AND superseded-by=<id present in proposal>), or
        - merged     (merged-into=<id present in proposal>).
     An ID that simply vanishes is a violation.
  4. Provenance: every NEW entry (ID not in the current playbook) carries a
     non-empty source slug and sha.
  5. No dangling pointers: every superseded-by / merged-into target resolves to an
     entry present in the proposal.

Usage:
    conservation_check.py --proposal proposals/<ts>-<slug>.md [--playbook playbook.md]
Exit code 0 = PASS, 1 = violations found, 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import dream_lib as dl


def _has_completion_marker(text: str) -> bool:
    return any(
        line.startswith(dl.COMPLETION_PREFIX) for line in text.splitlines()
    )


def check(playbook_text: str, proposal_text: str) -> list[str]:
    """Return a list of violation strings (empty list == PASS)."""
    violations: list[str] = []

    if not _has_completion_marker(proposal_text):
        violations.append(
            "proposal is missing the completion marker (partial/untrusted)"
        )

    try:
        current = dl.parse_markers(playbook_text)
    except ValueError as exc:
        return [f"current playbook has a malformed entry marker: {exc}"]
    try:
        proposed = dl.parse_markers(proposal_text)
    except ValueError as exc:
        return violations + [f"proposal has a malformed entry marker: {exc}"]

    # (2) duplicate IDs in proposal
    proposed_by_id: dict[str, dl.Entry] = {}
    for e in proposed:
        if e.id in proposed_by_id:
            violations.append(f"duplicate entry id in proposal: {e.id}")
        proposed_by_id[e.id] = e
    proposed_ids = set(proposed_by_id)
    current_ids = {e.id for e in current}

    # (3) conservation of every current entry
    for old in current:
        new = proposed_by_id.get(old.id)
        if new is None:
            violations.append(
                f"entry dropped: {old.id} present in playbook, absent from proposal "
                f"(no superseded-by / merged-into record)"
            )
            continue
        if new.status == "superseded":
            if not new.superseded_by:
                violations.append(
                    f"entry {old.id} marked superseded without a superseded-by target"
                )
            elif new.superseded_by not in proposed_ids:
                violations.append(
                    f"entry {old.id} superseded-by {new.superseded_by}, "
                    f"which is absent from the proposal"
                )
        elif new.merged_into:
            if new.merged_into not in proposed_ids:
                violations.append(
                    f"entry {old.id} merged-into {new.merged_into}, "
                    f"which is absent from the proposal"
                )
        # else: retained as active -> fine

    # (4) provenance on every NEW entry
    for e in proposed:
        if e.id in current_ids:
            continue
        if not e.source or not e.sha:
            violations.append(
                f"new entry {e.id} missing provenance "
                f"(source={e.source!r}, sha={e.sha!r})"
            )

    # (5) no dangling supersede/merge pointers
    for e in proposed:
        pointers = (("superseded-by", e.superseded_by), ("merged-into", e.merged_into))
        for label, target in pointers:
            if target and target not in proposed_ids:
                violations.append(
                    f"entry {e.id} has dangling {label}={target} (not in proposal)"
                )

    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate a proposal against the playbook."
    )
    ap.add_argument("--proposal", required=True, type=Path)
    ap.add_argument("--playbook", type=Path, default=None)
    args = ap.parse_args(argv)

    playbook = args.playbook if args.playbook is not None else dl.playbook_path()
    try:
        playbook_text = dl.read_text(playbook)
        proposal_text = dl.read_text(args.proposal)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    violations = check(playbook_text, proposal_text)
    if violations:
        print(f"CONSERVATION CHECK: FAIL ({len(violations)} violation(s))")
        for v in violations:
            print(f"  - {v}")
        return 1
    n_current = len(dl.parse_markers(playbook_text))
    n_proposed = len(dl.parse_markers(proposal_text))
    print(
        f"CONSERVATION CHECK: PASS "
        f"({n_current} existing entries conserved; {n_proposed} total in proposal)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
