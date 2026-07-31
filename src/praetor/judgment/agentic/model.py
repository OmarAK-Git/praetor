"""Model-calling protocols for the agentic judgment pipeline.

These Protocols are the seam between pipeline orchestration (phases.py)
and any concrete model backend. FakeSourceInvestigatorModel /
FakeHypothesisModel / FakeLeadModel (fake_model.py) are the only
implementations built in this plan; a real Gemini-backed implementation
translating these calls into function-calling wire traffic is deferred
follow-on work.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.agentic.budget import PhaseBudget


@dataclass(frozen=True)
class ToolCallDecision:
    """A source investigator's decision to invoke its bound tool."""

    arguments: dict[str, Any]


@dataclass(frozen=True)
class InvestigationSummary:
    """A source investigator's decision that it has gathered enough."""

    narrative: str


@dataclass(frozen=True)
class HypothesisCase:
    stance: str
    key_points: tuple[str, ...]
    cited_evidence_ids: tuple[str, ...]
    narrative: str


@runtime_checkable
class SourceInvestigatorModel(Protocol):
    def next_action(
        self, *, prior_call_count: int, last_call_succeeded: bool | None
    ) -> ToolCallDecision | InvestigationSummary:
        """Decide the next tool call, or conclude with a summary."""


@runtime_checkable
class HypothesisModel(Protocol):
    def build_case(
        self,
        *,
        stance: str,
        registry_facts: Sequence[EvidenceFact],
        budget: PhaseBudget,
    ) -> HypothesisCase:
        """Build the strongest case for ``stance`` from gathered facts."""


@runtime_checkable
class LeadModel(Protocol):
    def reconcile(
        self,
        *,
        registry_facts: Sequence[EvidenceFact],
        malicious_case: HypothesisCase,
        benign_case: HypothesisCase,
        budget: PhaseBudget,
    ) -> ModelJudgment:
        """Produce the final ModelJudgment from both hypothesis cases."""
