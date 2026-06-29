#!/usr/bin/env python3
"""Render the compact playbook digest agents read at startup.

`approve.py` regenerates this automatically after every promotion; this standalone
entry point is for manual regeneration (e.g. after a hand-edit to playbook.md, or
to refresh the digest without an approval). It makes no model calls and never
mutates playbook.md - it only writes the derived `playbook.digest.md`.

Usage:
    render_digest.py            # write .workflow/_dream/playbook.digest.md
    render_digest.py --stdout   # print the digest, write nothing
"""

from __future__ import annotations

import argparse
import sys

import dream_lib as dl


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the playbook digest.")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing")
    args = ap.parse_args(argv)

    pb = dl.parse_playbook(dl.read_text(dl.playbook_path()))
    body = dl.render_digest_text(pb)

    if args.stdout:
        sys.stdout.write(body)
        return 0

    dl.atomic_write(dl.digest_path(), body)
    n_total = len(pb.all_entries())
    n_active = sum(1 for e in pb.all_entries() if e.status == "active")
    print(
        f"digest written: {dl.digest_path().relative_to(dl.repo_root())} "
        f"({n_active} active / {n_total} total entries)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
