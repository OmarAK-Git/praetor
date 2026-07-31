"""Unit tests for agentic pipeline tools."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.config.helpers import preflight_path
from tests.config.shared import EXAMPLE_CONFIG

from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.policy import PolicyGateResult
from praetor.evidence.provenance import LEDGER_HISTORY
from praetor.judgment.agentic.tools import (
    LedgerHistoryTool,
    OrgConfigSectionTool,
    ScopeViolationError,
    SimilarCaseTool,
    WiderTelemetryTool,
)
from praetor.ledger.store import append_ledger_record, init_ledger_schema
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import open_state_store


def _judgment() -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
    )


def _edict_with_target(decision_id: str, target_id: str) -> DecisionEdict:
    now = datetime(2026, 7, 30, tzinfo=UTC)
    directive = ContainmentDirective(
        directive_id=f"dir-{decision_id}",
        decision_id=decision_id,
        target_type=TargetType.HOST,
        target_id=target_id,
        scope="global",
        evidence_refs=[],
        issued_at=now,
        expires_at=now,
        idempotency_key=f"idem-{decision_id}",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="deadbeef",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    return DecisionEdict(
        decision_id=decision_id,
        alert_reference="alert-x",
        evidence_bundle_hash="hash",
        org_config_snapshot_hash="cfg",
        live_never_contain_hash="deadbeef",
        model_judgment=_judgment(),
        policy_gate_result=PolicyGateResult(
            proposed_disposition=Disposition.STANDARD_REVIEW,
            final_disposition=Disposition.STANDARD_REVIEW,
        ),
        final_disposition=Disposition.STANDARD_REVIEW,
        system_fault_escalation=False,
        fault_flags=[],
        stamp_status="not_required",
        timing_metadata={},
        ledger_previous_hash=None,
        ledger_current_hash="pending",
        ticket_stamp_payload={},
        containment_directive=directive,
        decided_at=now,
    )


def test_ledger_history_tool_returns_facts_for_allowed_target(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict_with_target("d1", "HOST-1"))

    tool = LedgerHistoryTool(
        conn=store.conn,
        alert_reference="alert-x",
        allowed_target_ids=frozenset({"HOST-1"}),
    )
    result = tool.invoke({"target_ids": ["HOST-1"]})
    assert result.succeeded is True
    assert len(result.facts) == 1
    assert result.facts[0].provenance_path == LEDGER_HISTORY
    assert result.facts[0].normalized_fields["target_id"] == "HOST-1"


def test_ledger_history_tool_rejects_out_of_scope_target(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    tool = LedgerHistoryTool(
        conn=store.conn,
        alert_reference="alert-x",
        allowed_target_ids=frozenset({"HOST-1"}),
    )
    with pytest.raises(ScopeViolationError):
        tool.invoke({"target_ids": ["HOST-99"]})


def test_ledger_history_tool_defaults_to_all_allowed_targets(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict_with_target("d1", "HOST-1"))

    tool = LedgerHistoryTool(
        conn=store.conn,
        alert_reference="alert-x",
        allowed_target_ids=frozenset({"HOST-1"}),
    )
    result = tool.invoke({})
    assert result.succeeded is True
    assert len(result.facts) == 1


def _wider_fact(evidence_id: str) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"host_id": "HOST-1", "command_line": "x" * 500},
        source_event_reference="ref",
        raw_source="RAW-SECRET-DO-NOT-LEAK",
        provenance_path="sysmon_event_log",
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )


def test_wider_telemetry_tool_returns_all_facts_by_default() -> None:
    fact = _wider_fact("ev-1")
    tool = WiderTelemetryTool(facts_by_id={"ev-1": fact})
    result = tool.invoke({})
    assert result.succeeded is True
    assert result.facts == (fact,)


def test_wider_telemetry_tool_filters_by_requested_evidence_ids() -> None:
    fact1, fact2 = _wider_fact("ev-1"), _wider_fact("ev-2")
    tool = WiderTelemetryTool(facts_by_id={"ev-1": fact1, "ev-2": fact2})
    result = tool.invoke({"evidence_ids": ["ev-2"]})
    assert result.facts == (fact2,)


def test_wider_telemetry_tool_reports_unknown_evidence_id() -> None:
    tool = WiderTelemetryTool(facts_by_id={"ev-1": _wider_fact("ev-1")})
    result = tool.invoke({"evidence_ids": ["ev-does-not-exist"]})
    assert result.succeeded is False
    assert result.facts == ()


def test_wider_telemetry_tool_does_not_expose_raw_source_field_name_change() -> None:
    """Structural isolation guard (DEC-047 pattern): raw_source stays on the
    contract but this test pins that no *new* stringified excerpt path is
    introduced here that would bypass the excerpt truncation isolation
    layer — the tool returns EvidenceFact objects, not prompt text; the
    prompt-boundary exclusion of raw_source is exercised end-to-end in
    Task 12's provider test."""
    fact = _wider_fact("ev-1")
    tool = WiderTelemetryTool(facts_by_id={"ev-1": fact})
    result = tool.invoke({})
    assert result.facts[0].raw_source == "RAW-SECRET-DO-NOT-LEAK"


def _minimal_snapshot() -> OrgConfigSnapshot:
    return preflight_path(EXAMPLE_CONFIG)


def test_org_config_section_tool_returns_requested_section() -> None:
    snapshot = _minimal_snapshot()
    tool = OrgConfigSectionTool(snapshot=snapshot)
    result = tool.invoke({"section_name": "containment_policy"})
    assert result.succeeded is True
    assert result.section_name == "containment_policy"
    assert result.content != ""


def test_org_config_section_tool_rejects_unknown_section() -> None:
    snapshot = _minimal_snapshot()
    tool = OrgConfigSectionTool(snapshot=snapshot)
    result = tool.invoke({"section_name": "not_a_real_section"})
    assert result.succeeded is False
    assert result.content == ""


def test_similar_case_tool_returns_empty_when_no_precedents(tmp_path) -> None:
    store = open_state_store(tmp_path / "similar.db")
    tool = SimilarCaseTool(
        conn=store.conn,
        evidence_facts=({"normalized_fields": {"host_id": "HOST-1"}},),
    )
    result = tool.invoke({})
    assert result.succeeded is True
    assert result.exemplars == ()


def test_similar_case_tool_rejects_invalid_limit(tmp_path) -> None:
    store = open_state_store(tmp_path / "similar2.db")
    tool = SimilarCaseTool(conn=store.conn, evidence_facts=())
    result = tool.invoke({"limit": 0})
    assert result.succeeded is False
