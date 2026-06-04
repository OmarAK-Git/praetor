"""Task 10 — hash-chained ledger append and verification."""

from __future__ import annotations

import sqlite3

import pytest
from tests.ledger.conftest import (
    sample_decision_edict,
    sample_directive_revocation,
    sample_emergency_never_contain,
    sample_never_contain_snapshot,
)

from praetor.contracts.edict import DecisionEdict
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
)
from praetor.hashing import compute_never_contain_entries_hash
from praetor.ledger.hash_chain import (
    KNOWN_LEDGER_RECORD_TYPES,
    LedgerChainIntegrityError,
    verify_ledger_chain,
)
from praetor.ledger.store import append_ledger_record, fetch_ledger_rows
from praetor.state.sqlite_guard import StartupGuardError, critical_transaction


def _append(
    conn: sqlite3.Connection,
    record: (
        DecisionEdict
        | DirectiveRevocationRecord
        | NeverContainSnapshotRecord
        | EmergencyNeverContainRecord
    ),
) -> None:
    with critical_transaction(conn):
        append_ledger_record(conn, record)


def test_first_record_previous_hash_null(conn: sqlite3.Connection) -> None:
    edict = sample_decision_edict()
    _append(conn, edict)
    conn.commit()

    rows = fetch_ledger_rows(conn)
    assert len(rows) == 1
    assert rows[0].ledger_previous_hash is None
    stored = DecisionEdict.model_validate_json(rows[0].record_json)
    assert stored.ledger_previous_hash is None
    assert stored.ledger_current_hash == rows[0].ledger_current_hash
    verify_ledger_chain(conn)


def test_subsequent_records_chain(conn: sqlite3.Connection) -> None:
    first = sample_decision_edict(decision_id="dec-1")
    second = sample_decision_edict(decision_id="dec-2")
    _append(conn, first)
    _append(conn, second)
    conn.commit()

    rows = fetch_ledger_rows(conn)
    assert len(rows) == 2
    assert rows[1].ledger_previous_hash == rows[0].ledger_current_hash
    stored_second = DecisionEdict.model_validate_json(rows[1].record_json)
    assert stored_second.ledger_previous_hash == rows[0].ledger_current_hash
    verify_ledger_chain(conn)


def test_tampering_with_prior_record_detected(conn: sqlite3.Connection) -> None:
    _append(conn, sample_decision_edict(decision_id="dec-1"))
    _append(conn, sample_decision_edict(decision_id="dec-2"))
    conn.commit()

    conn.execute(
        """
        UPDATE ledger_chain
        SET record_json = json_set(record_json, '$.alert_reference', 'TAMPERED')
        WHERE chain_sequence = 1
        """
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError):
        verify_ledger_chain(conn)


def test_tampering_with_chain_hash_detected(conn: sqlite3.Connection) -> None:
    _append(conn, sample_decision_edict())
    conn.commit()

    conn.execute(
        """
        UPDATE ledger_chain
        SET ledger_current_hash = 'deadbeef'
        WHERE chain_sequence = 1
        """
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError):
        verify_ledger_chain(conn)


def test_interleaved_record_types_verify(conn: sqlite3.Connection) -> None:
    _append(conn, sample_decision_edict(decision_id="dec-1"))
    _append(conn, sample_never_contain_snapshot(decision_id="dec-1"))
    _append(conn, sample_emergency_never_contain())
    _append(conn, sample_directive_revocation())
    _append(conn, sample_decision_edict(decision_id="dec-2"))
    conn.commit()

    rows = fetch_ledger_rows(conn)
    assert [row.record_type for row in rows] == [
        "decision_edict",
        "never_contain_snapshot",
        "emergency_never_contain",
        "directive_revocation",
        "decision_edict",
    ]
    verify_ledger_chain(conn)


def test_unrecognized_record_type_is_integrity_violation(
    conn: sqlite3.Connection,
) -> None:
    _append(conn, sample_decision_edict())
    conn.commit()

    conn.execute(
        """
        UPDATE ledger_chain
        SET record_type = 'unknown_type',
            record_json = json_set(record_json, '$.record_type', 'unknown_type')
        WHERE chain_sequence = 1
        """
    )
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="unknown_type"):
        verify_ledger_chain(conn)


def test_append_requires_critical_transaction(conn: sqlite3.Connection) -> None:
    with pytest.raises(StartupGuardError, match="critical_transaction"):
        append_ledger_record(conn, sample_decision_edict())


def test_snapshot_content_covers_permanent_and_emergency(
    conn: sqlite3.Connection,
) -> None:
    content = [
        {
            "source": "permanent",
            "target_type": "host",
            "target_id": "host-permanent",
        },
        {
            "source": "emergency",
            "target_type": "host",
            "target_id": "host-emergency",
            "entry_id": "enc-1",
        },
    ]
    snapshot = sample_never_contain_snapshot(
        decision_id="dec-1",
        snapshot_content=content,
    )
    assert snapshot.snapshot_hash == compute_never_contain_entries_hash(content)
    _append(conn, snapshot)
    conn.commit()

    rows = fetch_ledger_rows(conn)
    stored = NeverContainSnapshotRecord.model_validate_json(rows[0].record_json)
    assert stored.snapshot_content == content
    verify_ledger_chain(conn)


def test_known_record_types_match_spec() -> None:
    assert KNOWN_LEDGER_RECORD_TYPES == frozenset(
        {
            "decision_edict",
            "directive_revocation",
            "never_contain_snapshot",
            "emergency_never_contain",
        }
    )
