"""TASK-002 scope guard (B-005): no Task 3+ packages or docs edits."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from praetor.contracts.schema_export import SCHEMA_EXPORTS, export_schemas

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "praetor"
SCHEMA_EXPORT_CLI = REPO_ROOT / "tools" / "schema_export.py"
COMMITTED_SCHEMAS = REPO_ROOT / "schemas"

FORBIDDEN_PACKAGES: tuple[str, ...] = ()

ALLOWED_PACKAGES: frozenset[str] = frozenset(
    {
        "alerts",
        "annotations",
        "auth",
        "codification",
        "config",
        "containment",
        "contracts",
        "correlation",
        "engine",
        "evidence",
        "hashing",
        "judgment",
        "ledger",
        "metrics",
        "policy",
        "reporting",
        "retrieval",
        "revocation",
        "runtime",
        "state",
        "tickets",
    }
)

SANCTIONED_V2_DOC_PATHS: frozenset[str] = frozenset(
    {
        "docs/contracts.md",
        "docs/plan.md",
        "docs/decisions.md",
        "docs/operator_runbook.md",
        "docs/architecture.md",
        "docs/eval_gates.md",
        "docs/proposals/delivery_backlog.md",
        "docs/proposals/v2_hardening.md",
    }
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
    assert children == ALLOWED_PACKAGES, (
        f"package allowlist drift: unexpected={children - ALLOWED_PACKAGES}, "
        f"missing={ALLOWED_PACKAGES - children}"
    )


def test_spec_md_not_sanctioned_doc() -> None:
    assert "docs/spec.md" not in SANCTIONED_V2_DOC_PATHS


def test_docs_changes_limited_to_sanctioned_v2_paths() -> None:
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
    unexpected = [path for path in changed if path not in SANCTIONED_V2_DOC_PATHS]
    msg = f"only sanctioned V2 docs may change under docs/: {unexpected}"
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


def test_committed_schemas_match_export() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        export_schemas(out)
        for _, filename in SCHEMA_EXPORTS:
            exported = (out / filename).read_bytes()
            committed = (COMMITTED_SCHEMAS / filename).read_bytes()
            assert exported == committed, filename


def test_schema_export_is_byte_stable() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        export_schemas(out)
        first = {p.name: p.read_bytes() for p in out.glob("*.json")}
        export_schemas(out)
        second = {p.name: p.read_bytes() for p in out.glob("*.json")}
    assert first == second


def test_schema_export_cli_exposes_check_and_write() -> None:
    result = subprocess.run(
        [sys.executable, str(SCHEMA_EXPORT_CLI), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    help_text = result.stdout
    assert "--check" in help_text
    assert "--write" in help_text


def test_schema_export_cli_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCHEMA_EXPORT_CLI), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
