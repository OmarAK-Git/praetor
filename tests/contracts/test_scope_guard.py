"""TASK-002 scope guard (B-005): no Task 3+ packages or docs edits."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "praetor"

FORBIDDEN_PACKAGES = (
    "state",
    "engine",
    "policy",
    "auth",
    "runtime",
    "tickets",
    "alerts",
    "containment",
)


def test_forbidden_packages_absent() -> None:
    for name in FORBIDDEN_PACKAGES:
        assert not (SRC / name).exists(), f"out-of-scope package present: {name}"


def test_only_expected_top_level_packages() -> None:
    children = {p.name for p in SRC.iterdir() if p.is_dir() and not p.name.startswith("_")}
    assert children <= {"contracts", "hashing"}, (
        f"unexpected packages: {children - {'contracts', 'hashing'}}"
    )


def test_docs_changes_limited_to_contracts_md() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "docs/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("git not available or not a git repo")
    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    unexpected = [path for path in changed if path != "docs/contracts.md"]
    assert unexpected == [], f"only docs/contracts.md may change in hashing tasks: {unexpected}"
