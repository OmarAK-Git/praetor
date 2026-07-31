"""Structural tests for the agentic model-calling Protocols."""

from __future__ import annotations

from praetor.judgment.agentic.model import (
    HypothesisCase,
    InvestigationSummary,
    ToolCallDecision,
)


def test_tool_call_decision_is_frozen() -> None:
    decision = ToolCallDecision(arguments={"target_ids": ["HOST-1"]})
    assert decision.arguments == {"target_ids": ["HOST-1"]}


def test_investigation_summary_holds_narrative() -> None:
    summary = InvestigationSummary(narrative="found nothing further")
    assert summary.narrative == "found nothing further"


def test_hypothesis_case_fields() -> None:
    case = HypothesisCase(
        stance="malicious",
        key_points=("unusual parent process",),
        cited_evidence_ids=("ev-1",),
        narrative="looks malicious",
    )
    assert case.stance == "malicious"
    assert case.key_points == ("unusual parent process",)
