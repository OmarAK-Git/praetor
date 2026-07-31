"""Deterministic Fake implementations of the agentic model Protocols, for
tests and the eval harness (mirrors judgment/fake_provider.py's role for
single-shot mode)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.model import (
    HypothesisCase,
    InvestigationSummary,
    ToolCallDecision,
)


@dataclass
class FakeSourceInvestigatorModel:
    """Replays a fixed, ordered call plan, then concludes with a summary."""

    call_plan: tuple[dict[str, object], ...] = ()
    summary_narrative: str = "investigation complete"
    calls_seen: int = field(default=0, init=False)

    def next_action(
        self, *, prior_call_count: int, last_call_succeeded: bool | None
    ) -> ToolCallDecision | InvestigationSummary:
        self.calls_seen += 1
        if prior_call_count < len(self.call_plan):
            return ToolCallDecision(arguments=dict(self.call_plan[prior_call_count]))
        return InvestigationSummary(narrative=self.summary_narrative)


@dataclass
class FakeHypothesisModel:
    case_factory: Callable[[str, Sequence[EvidenceFact]], HypothesisCase]

    def build_case(
        self,
        *,
        stance: str,
        registry_facts: Sequence[EvidenceFact],
        budget: PhaseBudget,
    ) -> HypothesisCase:
        _ = budget
        return self.case_factory(stance, registry_facts)


@dataclass
class FakeLeadModel:
    judgment_factory: Callable[..., ModelJudgment]

    def reconcile(
        self,
        *,
        registry_facts: Sequence[EvidenceFact],
        malicious_case: HypothesisCase,
        benign_case: HypothesisCase,
        budget: PhaseBudget,
    ) -> ModelJudgment:
        _ = budget
        return self.judgment_factory(
            registry_facts=registry_facts,
            malicious_case=malicious_case,
            benign_case=benign_case,
        )
