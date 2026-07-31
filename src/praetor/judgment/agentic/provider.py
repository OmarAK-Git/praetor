"""AgenticJudgmentProvider: a JudgmentProvider implementing the 3-phase
agentic pipeline. Drop-in replacement for single-shot providers at
whatever call site constructs the engine (no orchestrator.py branching
required — see spec's Rollout section)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from praetor.config.state import fetch_snapshot_by_hash
from praetor.contracts.judgment import ModelJudgment
from praetor.evidence.provenance import HOST_ID_FIELD
from praetor.judgment.agentic.budget import PhaseBudget
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.agentic.model import (
    HypothesisModel,
    LeadModel,
    SourceInvestigatorModel,
)
from praetor.judgment.agentic.phases import (
    run_hypothesis_debate,
    run_lead_reconciliation,
    run_source_fanout,
)
from praetor.judgment.agentic.registry import SessionEvidenceRegistry
from praetor.judgment.agentic.tools import (
    LedgerHistoryTool,
    OrgConfigSectionTool,
    SimilarCaseTool,
    WiderTelemetryTool,
)
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderProbeResult,
    ProviderUnavailableError,
)

DEFAULT_SOURCE_BUDGET = PhaseBudget(max_tool_calls=5, max_seconds=20.0)
DEFAULT_LEAD_BUDGET = PhaseBudget(max_tool_calls=0, max_seconds=15.0)


def _resolve_scope(request: JudgmentRequest) -> tuple[str, frozenset[str]]:
    assert request.evidence_bundle is not None
    target_ids = {
        str(fact.normalized_fields[HOST_ID_FIELD])
        for fact in request.evidence_bundle.facts
        if isinstance(fact.normalized_fields.get(HOST_ID_FIELD), str)
        and fact.normalized_fields[HOST_ID_FIELD].strip()
    }
    return request.scenario_id, frozenset(target_ids)


@dataclass(frozen=True)
class AgenticJudgmentProvider:
    conn: sqlite3.Connection
    make_ledger_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_org_config_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_similar_case_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_wider_telemetry_model: Callable[[JudgmentRequest], SourceInvestigatorModel]
    make_malicious_model: Callable[[JudgmentRequest], HypothesisModel]
    make_benign_model: Callable[[JudgmentRequest], HypothesisModel]
    make_lead_model: Callable[[JudgmentRequest], LeadModel]
    provider_name: str = "agentic"
    model_name: str = "agentic-pipeline-v1"
    source_budget: PhaseBudget = DEFAULT_SOURCE_BUDGET
    lead_budget: PhaseBudget = DEFAULT_LEAD_BUDGET

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        if request.evidence_bundle is None:
            msg = "agentic judgment requires request.evidence_bundle"
            raise ProviderUnavailableError(msg)

        alert_reference, allowed_target_ids = _resolve_scope(request)

        snapshot_hash = str(request.payload.get("org_config_snapshot_hash", ""))
        snapshot = fetch_snapshot_by_hash(self.conn, snapshot_hash)
        if snapshot is None:
            msg = f"no org config snapshot found for hash {snapshot_hash!r}"
            raise ProviderUnavailableError(msg)

        ledger_tool = LedgerHistoryTool(
            conn=self.conn,
            alert_reference=alert_reference,
            allowed_target_ids=allowed_target_ids,
        )
        org_config_tool = OrgConfigSectionTool(snapshot=snapshot)
        similar_case_tool = SimilarCaseTool(
            conn=self.conn,
            evidence_facts=tuple(
                fact.model_dump(mode="python") for fact in request.evidence_bundle.facts
            ),
        )
        wider_telemetry_tool = WiderTelemetryTool(
            facts_by_id={
                fact.evidence_id: fact for fact in request.evidence_bundle.facts
            }
        )

        registry = SessionEvidenceRegistry()
        fanout_result = run_source_fanout(
            ledger_model=self.make_ledger_model(request),
            ledger_tool=ledger_tool,
            org_config_model=self.make_org_config_model(request),
            org_config_tool=org_config_tool,
            similar_case_model=self.make_similar_case_model(request),
            similar_case_tool=similar_case_tool,
            wider_telemetry_model=self.make_wider_telemetry_model(request),
            wider_telemetry_tool=wider_telemetry_tool,
            budget=self.source_budget,
            registry=registry,
        )
        if fanout_result.all_failed:
            msg = f"all Phase 1 sources failed for scenario {request.scenario_id!r}"
            raise AgenticEvidenceGatheringFailedError(msg)

        malicious_case, benign_case = run_hypothesis_debate(
            malicious_model=self.make_malicious_model(request),
            benign_model=self.make_benign_model(request),
            registry=registry,
        )
        judgment = run_lead_reconciliation(
            lead_model=self.make_lead_model(request),
            registry=registry,
            malicious_case=malicious_case,
            benign_case=benign_case,
            budget=self.lead_budget,
        )
        return judgment.model_copy(
            update={
                "model_name": self.model_name,
                "provider_name": self.provider_name,
                "session_trace_hash": registry.session_trace_hash(),
            }
        )

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True,
            provider_name=self.provider_name,
            model_name=self.model_name,
            metadata={"canary_seen": bool(canary_payload)},
        )
