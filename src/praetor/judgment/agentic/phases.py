"""Phase orchestration for the agentic judgment pipeline.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, TypeVar

from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.agentic.budget import (
    BudgetExceededError,
    BudgetTracker,
    PhaseBudget,
)
from praetor.judgment.agentic.model import (
    HypothesisCase,
    HypothesisModel,
    InvestigationSummary,
    LeadModel,
    SourceInvestigatorModel,
)
from praetor.judgment.agentic.registry import (
    ExemplarCallRecord,
    OrgConfigCallRecord,
    SessionEvidenceRegistry,
    ToolCallRecord,
)
from praetor.judgment.agentic.tools import (
    ExemplarToolResult,
    LedgerHistoryTool,
    OrgConfigSectionResult,
    OrgConfigSectionTool,
    SimilarCaseTool,
    ToolResult,
    WiderTelemetryTool,
)

_T = TypeVar("_T")


def _drive_investigation(
    model: SourceInvestigatorModel,
    budget: PhaseBudget,
    invoke: Callable[[dict[str, Any]], tuple[bool, _T]],
) -> list[tuple[dict[str, Any], bool, _T]]:
    """Drive one source investigator's bounded loop.

    Returns a list of (query_arguments, succeeded, raw_result) in call
    order. Stops when the model signals InvestigationSummary or the
    budget is exhausted, whichever comes first.
    """
    tracker = BudgetTracker(budget=budget)
    last_succeeded: bool | None = None
    calls: list[tuple[dict[str, Any], bool, _T]] = []
    while True:
        action = model.next_action(
            prior_call_count=tracker.calls_made, last_call_succeeded=last_succeeded
        )
        if isinstance(action, InvestigationSummary):
            break
        try:
            tracker.consume_call()
        except BudgetExceededError:
            break
        succeeded, raw_result = invoke(action.arguments)
        calls.append((dict(action.arguments), succeeded, raw_result))
        last_succeeded = succeeded
    return calls


def _run_evidence_source(
    *,
    source: str,
    model: SourceInvestigatorModel,
    tool: LedgerHistoryTool | WiderTelemetryTool,
    budget: PhaseBudget,
) -> tuple[bool, list[ToolCallRecord]]:
    def invoke(arguments: dict[str, Any]) -> tuple[bool, ToolResult]:
        result = tool.invoke(arguments)
        return result.succeeded, result

    calls = _drive_investigation(model, budget, invoke)
    records = [
        ToolCallRecord(
            source=source,
            tool_name=tool.name,
            query=query,
            facts=result.facts,
            succeeded=succeeded,
            error=result.error,
        )
        for query, succeeded, result in calls
    ]
    return any(record.succeeded for record in records), records


def run_ledger_history_source(
    *, model: SourceInvestigatorModel, tool: LedgerHistoryTool, budget: PhaseBudget
) -> tuple[bool, list[ToolCallRecord]]:
    return _run_evidence_source(
        source="ledger_history", model=model, tool=tool, budget=budget
    )


def run_wider_telemetry_source(
    *, model: SourceInvestigatorModel, tool: WiderTelemetryTool, budget: PhaseBudget
) -> tuple[bool, list[ToolCallRecord]]:
    return _run_evidence_source(
        source="wider_telemetry", model=model, tool=tool, budget=budget
    )


def run_org_config_source(
    *, model: SourceInvestigatorModel, tool: OrgConfigSectionTool, budget: PhaseBudget
) -> tuple[bool, list[OrgConfigCallRecord]]:
    def invoke(arguments: dict[str, Any]) -> tuple[bool, OrgConfigSectionResult]:
        result = tool.invoke(arguments)
        return result.succeeded, result

    calls = _drive_investigation(model, budget, invoke)
    records = [
        OrgConfigCallRecord(
            source="org_config_section",
            tool_name=tool.name,
            query=query,
            section_name=result.section_name,
            content=result.content,
            succeeded=succeeded,
            error=result.error,
        )
        for query, succeeded, result in calls
    ]
    return any(record.succeeded for record in records), records


def run_similar_case_source(
    *, model: SourceInvestigatorModel, tool: SimilarCaseTool, budget: PhaseBudget
) -> tuple[bool, list[ExemplarCallRecord]]:
    def invoke(arguments: dict[str, Any]) -> tuple[bool, ExemplarToolResult]:
        result = tool.invoke(arguments)
        return result.succeeded, result

    calls = _drive_investigation(model, budget, invoke)
    records = [
        ExemplarCallRecord(
            source="similar_cases",
            tool_name=tool.name,
            query=query,
            exemplars=result.exemplars,
            succeeded=succeeded,
            error=result.error,
        )
        for query, succeeded, result in calls
    ]
    return any(record.succeeded for record in records), records


@dataclass(frozen=True)
class SourceFanoutResult:
    ledger_history_succeeded: bool
    org_config_succeeded: bool
    similar_cases_succeeded: bool
    wider_telemetry_succeeded: bool

    @property
    def all_failed(self) -> bool:
        return not (
            self.ledger_history_succeeded
            or self.org_config_succeeded
            or self.similar_cases_succeeded
            or self.wider_telemetry_succeeded
        )


def run_source_fanout(
    *,
    ledger_model: SourceInvestigatorModel,
    ledger_tool: LedgerHistoryTool,
    org_config_model: SourceInvestigatorModel,
    org_config_tool: OrgConfigSectionTool,
    similar_case_model: SourceInvestigatorModel,
    similar_case_tool: SimilarCaseTool,
    wider_telemetry_model: SourceInvestigatorModel,
    wider_telemetry_tool: WiderTelemetryTool,
    budget: PhaseBudget,
    registry: SessionEvidenceRegistry,
) -> SourceFanoutResult:
    """Run all four Phase 1 source investigators concurrently, then append
    their results to ``registry`` in a fixed deterministic order (ledger,
    org-config, similar-cases, wider-telemetry) regardless of which thread
    actually finished first — keeps session_trace_hash reproducible."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        ledger_future = executor.submit(
            run_ledger_history_source,
            model=ledger_model,
            tool=ledger_tool,
            budget=budget,
        )
        org_config_future = executor.submit(
            run_org_config_source,
            model=org_config_model,
            tool=org_config_tool,
            budget=budget,
        )
        similar_case_future = executor.submit(
            run_similar_case_source,
            model=similar_case_model,
            tool=similar_case_tool,
            budget=budget,
        )
        wider_telemetry_future = executor.submit(
            run_wider_telemetry_source,
            model=wider_telemetry_model,
            tool=wider_telemetry_tool,
            budget=budget,
        )
        ledger_succeeded, ledger_records = ledger_future.result()
        org_config_succeeded, org_config_records = org_config_future.result()
        similar_cases_succeeded, similar_case_records = similar_case_future.result()
        wider_telemetry_succeeded, wider_telemetry_records = (
            wider_telemetry_future.result()
        )

    for ledger_record in ledger_records:
        registry.record_evidence(ledger_record)
    for org_config_record in org_config_records:
        registry.record_org_config(org_config_record)
    for similar_case_record in similar_case_records:
        registry.record_exemplars(similar_case_record)
    for wider_telemetry_record in wider_telemetry_records:
        registry.record_evidence(wider_telemetry_record)

    return SourceFanoutResult(
        ledger_history_succeeded=ledger_succeeded,
        org_config_succeeded=org_config_succeeded,
        similar_cases_succeeded=similar_cases_succeeded,
        wider_telemetry_succeeded=wider_telemetry_succeeded,
    )


def run_hypothesis_debate(
    *,
    malicious_model: HypothesisModel,
    benign_model: HypothesisModel,
    registry: SessionEvidenceRegistry,
) -> tuple[HypothesisCase, HypothesisCase]:
    """Run both hypothesis debaters concurrently, reasoning-only over the
    Phase 1 registry (no new tool calls — see spec's Phase 2 tool-access
    decision)."""
    facts = registry.facts
    budget = PhaseBudget(max_tool_calls=0, max_seconds=15.0)
    with ThreadPoolExecutor(max_workers=2) as executor:
        malicious_future = executor.submit(
            malicious_model.build_case,
            stance="malicious",
            registry_facts=facts,
            budget=budget,
        )
        benign_future = executor.submit(
            benign_model.build_case,
            stance="benign",
            registry_facts=facts,
            budget=budget,
        )
        return malicious_future.result(), benign_future.result()


def run_lead_reconciliation(
    *,
    lead_model: LeadModel,
    registry: SessionEvidenceRegistry,
    malicious_case: HypothesisCase,
    benign_case: HypothesisCase,
    budget: PhaseBudget,
) -> ModelJudgment:
    """Produce the final ModelJudgment. ``budget`` must be a fixed,
    independent allotment for this phase — never derived from Phase 1/2
    leftover time — so reconciliation always has real time to run (spec's
    'protected minimum time allotment' requirement)."""
    return lead_model.reconcile(
        registry_facts=registry.facts,
        malicious_case=malicious_case,
        benign_case=benign_case,
        budget=budget,
    )
