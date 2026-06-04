"""Fixtures for ledger hash-chain tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from praetor.alerts.outbox import init_health_alert_outbox_schema
from praetor.contracts.disposition import Disposition
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
    RevocationReason,
)
from praetor.contracts.policy import PolicyGateResult
from praetor.ledger.store import init_ledger_schema
from praetor.state.sqlite_guard import create_guarded_connection, init_state_dir
from praetor.state.store import init_state_schema
from praetor.tickets.outbox import init_stamp_outbox_schema

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "state.db"
    init_state_dir(path)
    return path


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = create_guarded_connection(db_path)
    connection.row_factory = sqlite3.Row
    init_state_schema(connection)
    init_stamp_outbox_schema(connection)
    init_health_alert_outbox_schema(connection)
    init_ledger_schema(connection)
    connection.commit()
    yield connection
    connection.close()


def sample_model_judgment() -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[
            CitedEvidenceRef(evidence_id="ev-1", field_path="process_name"),
        ],
        key_tells=["suspicious parent"],
        org_config_refs=["containment_policy.default"],
        benign_alternatives=["admin tooling"],
        benign_alternatives_ruled_out=["none"],
        convergence_reasoning="multiple signals",
        narrative="summary",
        model_name="fake",
        provider_name="fake",
    )


def sample_policy_gate_result() -> PolicyGateResult:
    return PolicyGateResult(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        final_disposition=Disposition.STANDARD_REVIEW,
    )


def sample_decision_edict(*, decision_id: str = "dec-1") -> DecisionEdict:
    return DecisionEdict(
        decision_id=decision_id,
        alert_reference="ALERT-001",
        evidence_bundle_hash="sha256:bundle:abc",
        org_config_snapshot_hash="sha256:org:abc",
        live_never_contain_hash="sha256:nc:abc",
        model_judgment=sample_model_judgment(),
        policy_gate_result=sample_policy_gate_result(),
        final_disposition=Disposition.STANDARD_REVIEW,
        system_fault_escalation=False,
        fault_flags=[],
        stamp_status="succeeded",
        timing_metadata={},
        ledger_previous_hash="placeholder",
        ledger_current_hash="placeholder",
        ticket_stamp_payload={},
        decided_at=NOW,
    )


def sample_never_contain_snapshot(
    *,
    decision_id: str = "dec-1",
    snapshot_content: list[dict[str, object]] | None = None,
) -> NeverContainSnapshotRecord:
    content = snapshot_content if snapshot_content is not None else []
    from praetor.hashing import compute_never_contain_entries_hash

    return NeverContainSnapshotRecord(
        snapshot_id="snap-1",
        snapshot_hash=compute_never_contain_entries_hash(content),
        snapshot_content=content,
        evaluated_at=NOW,
        triggered_by_decision_id=decision_id,
    )


def sample_emergency_never_contain() -> EmergencyNeverContainRecord:
    added = NOW
    return EmergencyNeverContainRecord(
        entry_id="enc-1",
        target_specification={"target_type": "host", "target_id": "host-01"},
        added_by="soc-lead-1",
        added_at=added,
        expires_at=added + timedelta(hours=1),
        audit_reason="maintenance",
    )


def sample_directive_revocation() -> DirectiveRevocationRecord:
    return DirectiveRevocationRecord(
        revocation_id="rev-1",
        directive_id="dir-1",
        reason=RevocationReason.MANUAL,
        reason_code="manual_revocation",
        triggered_by="soc-lead-1",
        revoked_at=NOW,
        ledger_commit_at=NOW,
        idempotency_key_cleared=True,
    )
