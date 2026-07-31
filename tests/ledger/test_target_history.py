"""Unit tests for fetch_edicts_for_target_history (v1 LedgerHistoryTool
query surface — see spec's LedgerHistoryTool scope note)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.policy import PolicyGateResult
from praetor.ledger.store import (
    append_ledger_record,
    fetch_edicts_for_target_history,
    init_ledger_schema,
)
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


def _edict(
    decision_id: str, alert_reference: str, target_id: str | None
) -> DecisionEdict:
    directive = None
    if target_id is not None:
        now = datetime(2026, 7, 30, tzinfo=UTC)
        directive = ContainmentDirective(
            directive_id=f"dir-{decision_id}",
            decision_id=decision_id,
            target_type=TargetType.HOST,
            target_id=target_id,
            scope="global",
            evidence_refs=[],
            issued_at=now,
            expires_at=now.replace(second=now.second + 1) if now.second < 59 else now,
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
        alert_reference=alert_reference,
        evidence_bundle_hash="hash-" + decision_id,
        org_config_snapshot_hash="cfg-hash",
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
        decided_at=datetime(2026, 7, 30, tzinfo=UTC),
    )


def test_fetch_by_alert_reference(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict("d1", "alert-repeat", None))
        append_ledger_record(store.conn, _edict("d2", "alert-other", None))

    results = fetch_edicts_for_target_history(
        store.conn, alert_reference="alert-repeat", target_ids=()
    )
    assert [edict.decision_id for edict in results] == ["d1"]


def test_fetch_by_containment_target(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        append_ledger_record(store.conn, _edict("d1", "alert-a", "HOST-99"))
        append_ledger_record(store.conn, _edict("d2", "alert-b", "HOST-1"))

    results = fetch_edicts_for_target_history(
        store.conn, alert_reference="alert-unrelated", target_ids=("HOST-99",)
    )
    assert [edict.decision_id for edict in results] == ["d1"]


def test_fetch_respects_limit(tmp_path) -> None:
    store = open_state_store(tmp_path / "t.db")
    init_ledger_schema(store.conn)
    with critical_transaction(store.conn):
        for i in range(3):
            append_ledger_record(store.conn, _edict(f"d{i}", "alert-repeat", None))

    results = fetch_edicts_for_target_history(
        store.conn, alert_reference="alert-repeat", target_ids=(), limit=2
    )
    assert len(results) == 2
