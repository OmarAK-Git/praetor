"""Task 10 — edict / never_contain_snapshot audit relationship."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError
from tests.ledger.conftest import sample_decision_edict, sample_never_contain_snapshot

from praetor.contracts.ledger import NeverContainSnapshotRecord
from praetor.hashing import compute_never_contain_entries_hash
from praetor.ledger.hash_chain import (
    LedgerChainIntegrityError,
    verify_edict_has_matching_never_contain_snapshot,
    verify_edict_never_contain_audit_link,
)
from praetor.ledger.store import append_ledger_record, fetch_ledger_rows
from praetor.state.sqlite_guard import critical_transaction


def test_edict_live_hash_matches_chained_snapshot(conn: sqlite3.Connection) -> None:
    content = [
        {"target_type": "host", "target_id": "host-01", "source": "permanent"},
    ]
    content_hash = compute_never_contain_entries_hash(content)
    edict = sample_decision_edict(decision_id="dec-audit-1")
    edict = edict.model_copy(update={"live_never_contain_hash": content_hash})
    snapshot = sample_never_contain_snapshot(
        decision_id="dec-audit-1",
        snapshot_content=content,
    )

    with critical_transaction(conn):
        append_ledger_record(conn, edict)
        append_ledger_record(conn, snapshot)
    conn.commit()

    stored_edict = fetch_ledger_rows(conn)[0]
    from praetor.contracts.edict import DecisionEdict

    parsed_edict = DecisionEdict.model_validate_json(stored_edict.record_json)
    verify_edict_has_matching_never_contain_snapshot(conn, parsed_edict)


def test_edict_live_hash_mismatch_raises(conn: sqlite3.Connection) -> None:
    content = [{"target_type": "host", "target_id": "host-01"}]
    edict = sample_decision_edict(decision_id="dec-audit-2")
    edict = edict.model_copy(update={"live_never_contain_hash": "sha256:wrong"})
    snapshot = sample_never_contain_snapshot(
        decision_id="dec-audit-2",
        snapshot_content=content,
    )

    with critical_transaction(conn):
        append_ledger_record(conn, edict)
        append_ledger_record(conn, snapshot)
    conn.commit()

    from praetor.contracts.edict import DecisionEdict

    row = fetch_ledger_rows(conn)[0]
    parsed_edict = DecisionEdict.model_validate_json(row.record_json)
    with pytest.raises(LedgerChainIntegrityError, match="live_never_contain_hash"):
        verify_edict_has_matching_never_contain_snapshot(conn, parsed_edict)


def test_missing_snapshot_for_edict_raises(conn: sqlite3.Connection) -> None:
    edict = sample_decision_edict(decision_id="dec-no-snap")
    with critical_transaction(conn):
        append_ledger_record(conn, edict)
    conn.commit()

    from praetor.contracts.edict import DecisionEdict

    row = fetch_ledger_rows(conn)[0]
    parsed_edict = DecisionEdict.model_validate_json(row.record_json)
    with pytest.raises(LedgerChainIntegrityError, match="no never_contain_snapshot"):
        verify_edict_has_matching_never_contain_snapshot(conn, parsed_edict)


def test_snapshot_hash_mismatch_rejected_at_validation() -> None:
    with pytest.raises(ValidationError, match="snapshot_hash"):
        NeverContainSnapshotRecord(
            snapshot_id="snap-bad",
            snapshot_hash="not-the-right-hash",
            snapshot_content=[{"target_type": "host", "target_id": "h1"}],
            evaluated_at=sample_never_contain_snapshot().evaluated_at,
            triggered_by_decision_id="dec-1",
        )


def test_audit_link_rejects_decision_id_mismatch() -> None:
    content = [{"target_type": "host", "target_id": "host-01"}]
    edict = sample_decision_edict(decision_id="dec-a")
    content_hash = compute_never_contain_entries_hash(content)
    edict = edict.model_copy(update={"live_never_contain_hash": content_hash})
    snapshot = sample_never_contain_snapshot(
        decision_id="dec-b",
        snapshot_content=content,
    )
    with pytest.raises(LedgerChainIntegrityError, match="triggered_by_decision_id"):
        verify_edict_never_contain_audit_link(edict, snapshot)
