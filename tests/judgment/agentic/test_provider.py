"""End-to-end tests for AgenticJudgmentProvider, wired entirely with Fakes."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from tests.config.helpers import preflight_path
from tests.config.shared import EXAMPLE_CONFIG

from praetor.config.state import persist_org_config_snapshot
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.judgment.agentic.errors import AgenticEvidenceGatheringFailedError
from praetor.judgment.agentic.fake_model import (
    FakeHypothesisModel,
    FakeLeadModel,
    FakeSourceInvestigatorModel,
)
from praetor.judgment.agentic.model import HypothesisCase
from praetor.judgment.agentic.provider import AgenticJudgmentProvider
from praetor.judgment.provider import JudgmentRequest, ProviderUnavailableError
from praetor.state.store import StateStore, open_state_store


def _open_thread_safe_store(tmp_path) -> StateStore:
    """Phase 1 fan-out uses threads; reopen conn with check_same_thread=False."""
    store = open_state_store(tmp_path / "t.db")
    db_path = store.db_path
    store.conn.close()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    return StateStore(conn=conn, db_path=db_path)


def _bundle() -> EvidenceBundle:
    fact = EvidenceFact(
        evidence_id="ev-1",
        normalized_fields={"host_id": "HOST-1"},
        source_event_reference="ref",
        raw_source="raw",
        provenance_path="sysmon_event_log",
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )
    return EvidenceBundle(facts=[fact])


def _bind_org_config(store) -> str:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    persist_org_config_snapshot(
        store.conn, snapshot, verbatim_render_text="test-render"
    )
    store.conn.commit()
    return snapshot.snapshot_hash


def _passthrough_hypothesis_model(stance: str) -> FakeHypothesisModel:
    return FakeHypothesisModel(
        case_factory=lambda s, facts: HypothesisCase(
            stance=s, key_points=(), cited_evidence_ids=(), narrative=""
        )
    )


def _passthrough_lead_model(
    disposition: Disposition = Disposition.STANDARD_REVIEW,
) -> FakeLeadModel:
    return FakeLeadModel(
        judgment_factory=lambda **kwargs: skeleton_model_judgment(proposed=disposition)
    )


def _make_provider(store, *, all_sources_fail: bool = False) -> AgenticJudgmentProvider:
    plan = () if all_sources_fail else ({},)
    return AgenticJudgmentProvider(
        conn=store.conn,
        make_ledger_model=lambda request: FakeSourceInvestigatorModel(call_plan=plan),
        make_org_config_model=lambda request: FakeSourceInvestigatorModel(
            call_plan=()
        ),
        make_similar_case_model=lambda request: FakeSourceInvestigatorModel(
            call_plan=()
        ),
        make_wider_telemetry_model=lambda request: FakeSourceInvestigatorModel(
            call_plan=plan
        ),
        make_malicious_model=lambda request: _passthrough_hypothesis_model("malicious"),
        make_benign_model=lambda request: _passthrough_hypothesis_model("benign"),
        make_lead_model=lambda request: _passthrough_lead_model(),
    )


def test_generate_judgment_requires_evidence_bundle(tmp_path) -> None:
    store = _open_thread_safe_store(tmp_path)
    provider = _make_provider(store)
    request = JudgmentRequest(
        scenario_id="s1", payload={"org_config_snapshot_hash": "h"}
    )
    with pytest.raises(ProviderUnavailableError):
        provider.generate_judgment(request)


def test_generate_judgment_end_to_end_with_fakes(tmp_path) -> None:
    store = _open_thread_safe_store(tmp_path)
    snapshot_hash = _bind_org_config(store)
    provider = _make_provider(store)
    request = JudgmentRequest(
        scenario_id="s1",
        payload={"org_config_snapshot_hash": snapshot_hash},
        evidence_bundle=_bundle(),
    )
    judgment = provider.generate_judgment(request)
    assert judgment.model_name == "agentic-pipeline-v1"
    assert judgment.provider_name == "agentic"
    assert judgment.session_trace_hash is not None
    assert len(judgment.session_trace_hash) == 64


def test_generate_judgment_raises_when_all_sources_fail(tmp_path) -> None:
    store = _open_thread_safe_store(tmp_path)
    snapshot_hash = _bind_org_config(store)
    provider = _make_provider(store, all_sources_fail=True)
    request = JudgmentRequest(
        scenario_id="s1",
        payload={"org_config_snapshot_hash": snapshot_hash},
        evidence_bundle=_bundle(),
    )
    with pytest.raises(AgenticEvidenceGatheringFailedError):
        provider.generate_judgment(request)


def test_probe_reports_success() -> None:

    provider = AgenticJudgmentProvider(
        conn=None,  # type: ignore[arg-type]
        make_ledger_model=lambda request: FakeSourceInvestigatorModel(),
        make_org_config_model=lambda request: FakeSourceInvestigatorModel(),
        make_similar_case_model=lambda request: FakeSourceInvestigatorModel(),
        make_wider_telemetry_model=lambda request: FakeSourceInvestigatorModel(),
        make_malicious_model=lambda request: _passthrough_hypothesis_model("malicious"),
        make_benign_model=lambda request: _passthrough_hypothesis_model("benign"),
        make_lead_model=lambda request: _passthrough_lead_model(),
    )
    result = provider.probe({"canary": "x"})
    assert result.success is True
