"""V2-037 Gate 5 intake wiring: evaluation recording + exemplar injection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from tests.ledger.conftest import sample_decision_edict, sample_model_judgment
from tests.policy.conftest import (
    auto_contain_judgment,
    host_auto_contain_policy,
    host_bundle,
    persist_snapshot_with_overrides,
)

from praetor.annotations.store import submit_annotation
from praetor.auth import Principal, PrincipalMapVerifier
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    process_alert_intake,
)
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderProbeResult,
)
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import critical_transaction

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
ANALYST_TOKEN = "token-analyst"


@pytest.fixture
def analyst_verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {ANALYST_TOKEN: Principal(identity="analyst@example.com", role="analyst")}
    )


@dataclass
class _CapturingJudgmentProvider:
    judgment: ModelJudgment
    last_request: JudgmentRequest | None = None
    calls: int = 0
    captured_payloads: list[dict[str, object]] = field(default_factory=list)

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.last_request = request
        self.captured_payloads.append(dict(request.payload))
        self.calls += 1
        return self.judgment

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        _ = canary_payload
        return ProviderProbeResult(
            success=True,
            provider_name="capturing",
            model_name="test",
            metadata={},
        )


def _append_edict(
    conn: Any,
    *,
    decision_id: str,
    alert_reference: str,
    narrative: str,
) -> None:
    judgment = sample_model_judgment()
    judgment = ModelJudgment(
        **{
            **judgment.model_dump(),
            "narrative": narrative,
            "key_tells": narrative.split(),
        }
    )
    edict = sample_decision_edict(decision_id=decision_id)
    edict = edict.model_copy(
        update={
            "alert_reference": alert_reference,
            "model_judgment": judgment,
        }
    )
    with critical_transaction(conn):
        append_ledger_record(conn, edict)
    conn.commit()


def _confirm_decision(
    conn: Any,
    verifier: PrincipalMapVerifier,
    *,
    decision_id: str,
    comment: str,
) -> None:
    with critical_transaction(conn):
        submit_annotation(
            conn,
            token=ANALYST_TOKEN,
            verifier=verifier,
            decision_id=decision_id,
            disposition_correct=True,
            corrected_disposition=None,
            comment=comment,
            timestamp=NOW,
        )
    conn.commit()


def _evaluation_row(conn: Any, decision_id: str) -> Any:
    return conn.execute(
        """
        SELECT decision_id, target_type, asset_class, proposed_disposition,
               final_disposition, overridden
        FROM policy_gate_evaluations
        WHERE decision_id = ?
        """,
        (decision_id,),
    ).fetchone()


def test_intake_persists_policy_gate_evaluation_on_auto_contain(activated) -> None:
    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        activated,
        snapshot,
        containment_policy=host_auto_contain_policy(),
    )
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CapturingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-GATE5-AUTO-CONTAIN",
        evidence_bundle=bundle,
    )
    assert result.decision_id is not None
    assert result.disposition == Disposition.AUTO_CONTAIN

    row = _evaluation_row(activated.conn, result.decision_id)
    assert row is not None
    assert row["target_type"] == "host"
    assert row["asset_class"] == "ungrouped"
    assert row["proposed_disposition"] == Disposition.AUTO_CONTAIN.value
    assert row["final_disposition"] == Disposition.AUTO_CONTAIN.value
    assert int(row["overridden"]) == 0


def test_intake_persists_policy_gate_evaluation_on_escalate(activated) -> None:
    bundle = host_bundle(host_id="dc-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CapturingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-GATE5-ESCALATE",
        evidence_bundle=bundle,
    )
    assert result.decision_id is not None
    assert result.disposition == Disposition.ESCALATE

    row = _evaluation_row(activated.conn, result.decision_id)
    assert row is not None
    assert row["target_type"] == "unknown"
    assert row["asset_class"] == "unknown"
    assert row["proposed_disposition"] == Disposition.AUTO_CONTAIN.value
    assert row["final_disposition"] == Disposition.ESCALATE.value
    assert int(row["overridden"]) == 1


def test_intake_injects_similar_case_exemplars_when_precedents_exist(
    activated,
    analyst_verifier: PrincipalMapVerifier,
) -> None:
    _append_edict(
        activated.conn,
        decision_id="dec-precedent",
        alert_reference="ALERT-PRECEDENT",
        narrative="cmd.exe host containment confirmed precedent",
    )
    _confirm_decision(
        activated.conn,
        analyst_verifier,
        decision_id="dec-precedent",
        comment="confirmed cmd.exe case",
    )

    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        activated,
        snapshot,
        containment_policy=host_auto_contain_policy(),
    )
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CapturingJudgmentProvider(judgment=judgment)
    process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-GATE5-EXEMPLAR",
        evidence_bundle=bundle,
    )

    assert provider.last_request is not None
    payload = provider.last_request.payload
    assert "prompt_exemplar_block" in payload
    exemplars = payload["prompt_exemplar_block"]["exemplars"]
    assert exemplars[0]["source_case_id"] == "ALERT-PRECEDENT"


def test_intake_omits_exemplar_block_without_precedents(activated) -> None:
    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        activated,
        snapshot,
        containment_policy=host_auto_contain_policy(),
    )
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CapturingJudgmentProvider(judgment=judgment)
    process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-GATE5-NO-EXEMPLAR",
        evidence_bundle=bundle,
    )

    assert provider.last_request is not None
    assert "prompt_exemplar_block" not in provider.last_request.payload
