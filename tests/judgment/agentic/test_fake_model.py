"""Unit tests for deterministic Fake model implementations."""

from __future__ import annotations

from praetor.contracts.disposition import Disposition
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.fake_model import (
    FakeHypothesisModel,
    FakeLeadModel,
    FakeSourceInvestigatorModel,
)
from praetor.judgment.agentic.model import (
    HypothesisCase,
    InvestigationSummary,
    ToolCallDecision,
)


def test_fake_source_investigator_replays_call_plan_then_summarizes() -> None:
    model = FakeSourceInvestigatorModel(
        call_plan=({"target_ids": ["HOST-1"]}, {"target_ids": ["HOST-1", "HOST-2"]})
    )
    first = model.next_action(prior_call_count=0, last_call_succeeded=None)
    assert isinstance(first, ToolCallDecision)
    assert first.arguments == {"target_ids": ["HOST-1"]}

    second = model.next_action(prior_call_count=1, last_call_succeeded=True)
    assert isinstance(second, ToolCallDecision)

    third = model.next_action(prior_call_count=2, last_call_succeeded=True)
    assert isinstance(third, InvestigationSummary)


def test_fake_hypothesis_model_delegates_to_factory() -> None:
    model = FakeHypothesisModel(
        case_factory=lambda stance, facts: HypothesisCase(
            stance=stance,
            key_points=(f"{len(facts)} facts seen",),
            cited_evidence_ids=(),
            narrative="",
        )
    )
    case = model.build_case(
        stance="malicious",
        registry_facts=(),
        budget=PhaseBudget(max_tool_calls=0, max_seconds=1.0),
    )
    assert case.stance == "malicious"
    assert case.key_points == ("0 facts seen",)


def test_fake_lead_model_delegates_to_factory() -> None:
    from praetor.engine.skeleton import skeleton_model_judgment

    model = FakeLeadModel(
        judgment_factory=lambda **kwargs: skeleton_model_judgment(
            proposed=Disposition.ESCALATE
        )
    )
    malicious = HypothesisCase(
        stance="malicious", key_points=(), cited_evidence_ids=(), narrative=""
    )
    benign = HypothesisCase(
        stance="benign", key_points=(), cited_evidence_ids=(), narrative=""
    )
    judgment = model.reconcile(
        registry_facts=(),
        malicious_case=malicious,
        benign_case=benign,
        budget=PhaseBudget(max_tool_calls=0, max_seconds=1.0),
    )
    assert judgment.proposed_disposition == Disposition.ESCALATE
