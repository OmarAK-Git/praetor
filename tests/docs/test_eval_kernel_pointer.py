from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_eval_gates_points_at_sprint1_plan() -> None:
    text = (REPO / "docs" / "eval_gates.md").read_text(encoding="utf-8")
    assert "2026-09-07-eval-kernel-sprint1.md" in text
    assert "eval-kernel.yml" in text
    assert "FakeProvider" in text
    assert "cite-to-subject" in text


def test_memory_bank_points_at_sprint1_plan() -> None:
    active = (REPO / "memory-bank" / "activeContext.md").read_text(encoding="utf-8")
    tasks = (REPO / "memory-bank" / "tasks.md").read_text(encoding="utf-8")
    assert "2026-09-07-eval-kernel-sprint1.md" in active
    assert "2026-09-07-eval-kernel-sprint1.md" in tasks
