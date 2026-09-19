from __future__ import annotations

from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "eval-kernel.yml"
)


def test_eval_kernel_workflow_is_not_notebook_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pip install -e \".[dev]\"" in text or "pip install -e '.[dev]'" in text
    assert "pytest tests/evals/" in text
    assert "python -m evals.harness --all" in text
    assert "nbconvert" not in text
    assert "PRAETOR_REAL_PROVIDER_PROBE" not in text
    assert "PRAETOR_CAPABILITY_SPIKE" not in text
