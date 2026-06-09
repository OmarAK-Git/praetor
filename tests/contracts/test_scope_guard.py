"""TASK-002 scope guard (B-005): no Task 3+ packages or docs edits."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "praetor"

FORBIDDEN_PACKAGES = (
    "containment",
)

SQLITE_GUARD = SRC / "state" / "sqlite_guard.py"
_BARE_BEGIN = re.compile(r"\bBEGIN\b(?!\s+IMMEDIATE\b)", re.IGNORECASE)


def _string_has_forbidden_begin(value: str) -> bool:
    upper = value.upper()
    if "BEGIN DEFERRED" in upper or "BEGIN EXCLUSIVE" in upper:
        return True
    return _BARE_BEGIN.search(value) is not None


def _find_forbidden_begin_literals(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _string_has_forbidden_begin(node.value):
                hits.append((node.lineno, node.value))
    return hits


def test_forbidden_packages_absent() -> None:
    for name in FORBIDDEN_PACKAGES:
        assert not (SRC / name).exists(), f"out-of-scope package present: {name}"


def test_only_expected_top_level_packages() -> None:
    children = {
        p.name for p in SRC.iterdir() if p.is_dir() and not p.name.startswith("_")
    }
    allowed = {
        "alerts",
        "auth",
        "config",
        "contracts",
        "engine",
        "evidence",
        "hashing",
        "judgment",
        "ledger",
        "policy",
        "revocation",
        "runtime",
        "state",
        "tickets",
    }
    assert children <= allowed, f"unexpected packages: {children - allowed}"


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
    allowed = {"docs/contracts.md", "docs/plan.md"}
    unexpected = [path for path in changed if path not in allowed]
    msg = f"only scoped Phase 1 docs may change under docs/: {unexpected}"
    assert unexpected == [], msg


def test_no_bare_begin_outside_sqlite_guard() -> None:
    violations: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path == SQLITE_GUARD:
            continue
        for lineno, literal in _find_forbidden_begin_literals(path):
            rel = path.relative_to(REPO_ROOT)
            violations.append(f"{rel}:{lineno}: {literal!r}")
    assert violations == [], (
        "bare BEGIN outside sqlite_guard.py:\n" + "\n".join(violations)
    )
