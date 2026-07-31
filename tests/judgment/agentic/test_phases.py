"""Unit tests for the Phase 1 source fan-out driver."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceFact
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.evidence.provenance import LEDGER_HISTORY
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.fake_model import (
    FakeHypothesisModel,
    FakeLeadModel,
    FakeSourceInvestigatorModel,
)
from praetor.judgment.agentic.model import HypothesisCase
from praetor.judgment.agentic.phases import (
    run_hypothesis_debate,
    run_lead_reconciliation,
    run_source_fanout,
)
from praetor.judgment.agentic.registry import SessionEvidenceRegistry, ToolCallRecord
from praetor.judgment.agentic.tools import (
    ExemplarToolResult,
    OrgConfigSectionResult,
    ToolResult,
)


def _fact() -> EvidenceFact:
    return EvidenceFact(
        evidence_id="ev-1",
        normalized_fields={"host_id": "HOST-1"},
        source_event_reference="ref",
        raw_source="raw",
        provenance_path=LEDGER_HISTORY,
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )


class _StubTool:
    name = "stub"

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def invoke(self, arguments: dict[str, object]) -> object:
        self.calls.append(dict(arguments))
        return self.result


def test_fanout_runs_all_four_sources_and_records_registry() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=3, max_seconds=5.0)

    ledger_tool = _StubTool(ToolResult(facts=(_fact(),), succeeded=True))
    org_config_tool = _StubTool(
        OrgConfigSectionResult(
            section_name="containment_policy", content="{}", succeeded=True
        )
    )
    similar_case_tool = _StubTool(
        ExemplarToolResult(exemplars=({"exemplar_id": "p1"},), succeeded=True)
    )
    wider_telemetry_tool = _StubTool(ToolResult(facts=(), succeeded=True))

    result = run_source_fanout(
        ledger_model=FakeSourceInvestigatorModel(
            call_plan=({"target_ids": ["HOST-1"]},)
        ),
        ledger_tool=ledger_tool,
        org_config_model=FakeSourceInvestigatorModel(
            call_plan=({"section_name": "containment_policy"},)
        ),
        org_config_tool=org_config_tool,
        similar_case_model=FakeSourceInvestigatorModel(call_plan=({},)),
        similar_case_tool=similar_case_tool,
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=({},)),
        wider_telemetry_tool=wider_telemetry_tool,
        budget=budget,
        registry=registry,
    )

    assert result.ledger_history_succeeded is True
    assert result.org_config_succeeded is True
    assert result.similar_cases_succeeded is True
    assert result.wider_telemetry_succeeded is True
    assert result.all_failed is False
    assert len(registry.facts) == 1
    assert len(registry.exemplars) == 1
    assert len(registry.org_config_findings) == 1


def test_fanout_all_sources_failed_marks_all_failed() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=1, max_seconds=5.0)

    failing_evidence_tool = _StubTool(
        ToolResult(facts=(), succeeded=False, error="boom")
    )
    failing_org_config_tool = _StubTool(
        OrgConfigSectionResult(
            section_name="x", content="", succeeded=False, error="boom"
        )
    )
    failing_exemplar_tool = _StubTool(
        ExemplarToolResult(exemplars=(), succeeded=False, error="boom")
    )

    result = run_source_fanout(
        ledger_model=FakeSourceInvestigatorModel(call_plan=({},)),
        ledger_tool=failing_evidence_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=({},)),
        org_config_tool=failing_org_config_tool,
        similar_case_model=FakeSourceInvestigatorModel(call_plan=({},)),
        similar_case_tool=failing_exemplar_tool,
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=({},)),
        wider_telemetry_tool=failing_evidence_tool,
        budget=budget,
        registry=registry,
    )

    assert result.all_failed is True


def test_fanout_partial_failure_does_not_mark_all_failed() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=1, max_seconds=5.0)

    ok_tool = _StubTool(ToolResult(facts=(_fact(),), succeeded=True))
    failing_evidence_tool = _StubTool(
        ToolResult(facts=(), succeeded=False, error="boom")
    )
    failing_org_config_tool = _StubTool(
        OrgConfigSectionResult(
            section_name="x", content="", succeeded=False, error="boom"
        )
    )
    failing_exemplar_tool = _StubTool(
        ExemplarToolResult(exemplars=(), succeeded=False, error="boom")
    )

    result = run_source_fanout(
        ledger_model=FakeSourceInvestigatorModel(call_plan=({},)),
        ledger_tool=ok_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=({},)),
        org_config_tool=failing_org_config_tool,
        similar_case_model=FakeSourceInvestigatorModel(call_plan=({},)),
        similar_case_tool=failing_exemplar_tool,
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=({},)),
        wider_telemetry_tool=failing_evidence_tool,
        budget=budget,
        registry=registry,
    )

    assert result.all_failed is False
    assert result.ledger_history_succeeded is True
    assert result.org_config_succeeded is False


def test_fanout_respects_budget_and_stops_calling() -> None:
    registry = SessionEvidenceRegistry()
    budget = PhaseBudget(max_tool_calls=1, max_seconds=5.0)
    ok_tool = _StubTool(ToolResult(facts=(_fact(),), succeeded=True))

    # call_plan has 3 entries but budget only allows 1 call.
    over_budget_model = FakeSourceInvestigatorModel(
        call_plan=({"a": 1}, {"a": 2}, {"a": 3})
    )

    result = run_source_fanout(
        ledger_model=over_budget_model,
        ledger_tool=ok_tool,
        org_config_model=FakeSourceInvestigatorModel(call_plan=()),
        org_config_tool=_StubTool(
            OrgConfigSectionResult(section_name="x", content="{}", succeeded=True)
        ),
        similar_case_model=FakeSourceInvestigatorModel(call_plan=()),
        similar_case_tool=_StubTool(ExemplarToolResult(exemplars=(), succeeded=True)),
        wider_telemetry_model=FakeSourceInvestigatorModel(call_plan=()),
        wider_telemetry_tool=_StubTool(ToolResult(facts=(), succeeded=True)),
        budget=budget,
        registry=registry,
    )
    assert result.ledger_history_succeeded is True
    assert len(ok_tool.calls) == 1


def test_hypothesis_debate_runs_both_stances() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={},
            facts=(_fact(),),
            succeeded=True,
        )
    )
    malicious_model = FakeHypothesisModel(
        case_factory=lambda stance, facts: HypothesisCase(
            stance=stance,
            key_points=(f"{len(facts)}-facts",),
            cited_evidence_ids=(),
            narrative="",
        )
    )
    benign_model = FakeHypothesisModel(
        case_factory=lambda stance, facts: HypothesisCase(
            stance=stance,
            key_points=("benign-explanation",),
            cited_evidence_ids=(),
            narrative="",
        )
    )
    malicious_case, benign_case = run_hypothesis_debate(
        malicious_model=malicious_model,
        benign_model=benign_model,
        registry=registry,
    )
    assert malicious_case.stance == "malicious"
    assert malicious_case.key_points == ("1-facts",)
    assert benign_case.stance == "benign"


def test_lead_reconciliation_produces_judgment() -> None:
    registry = SessionEvidenceRegistry()
    malicious_case = HypothesisCase(
        stance="malicious", key_points=(), cited_evidence_ids=(), narrative=""
    )
    benign_case = HypothesisCase(
        stance="benign", key_points=(), cited_evidence_ids=(), narrative=""
    )
    lead_model = FakeLeadModel(
        judgment_factory=lambda **kwargs: skeleton_model_judgment(
            proposed=Disposition.ESCALATE
        )
    )
    judgment = run_lead_reconciliation(
        lead_model=lead_model,
        registry=registry,
        malicious_case=malicious_case,
        benign_case=benign_case,
        budget=PhaseBudget(max_tool_calls=0, max_seconds=15.0),
    )
    assert judgment.proposed_disposition == Disposition.ESCALATE
