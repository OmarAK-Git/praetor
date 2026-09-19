from __future__ import annotations

import ast
from pathlib import Path

from evals.e2e_kernel import run_e2e_kernel
from evals.scorecard import validate_scorecard_row

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_kernel_module_does_not_import_flatten() -> None:
    tree = ast.parse(
        (REPO_ROOT / "evals" / "e2e_kernel.py").read_text(encoding="utf-8")
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "evals.capability.flatten"
            assert not (node.module or "").startswith("evals.capability.flatten")


def test_path_b_stays_out_of_src_both_arms(tmp_path: Path) -> None:
    rows = [
        row
        for row in run_e2e_kernel(tmp_root=tmp_path)
        if row.scenario_id == "des.path_b_stays_out_of_src"
    ]
    assert {row.arm for row in rows} == {"old_build", "new_build"}
    for row in rows:
        validate_scorecard_row(row)
        assert row.status == "pass"
        assert row.observed["path_b_import_found"] is False
        assert row.failure_class == "none"
