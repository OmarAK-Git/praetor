"""V2-019 — optional ledger tip anchor verification."""

from __future__ import annotations

import sqlite3

import pytest
from tests.ledger.conftest import sample_decision_edict

from praetor.ledger.hash_chain import LedgerChainIntegrityError
from praetor.ledger.store import append_ledger_record, fetch_ledger_tip_hash
from praetor.ledger.tip_anchor import (
    LedgerTipAnchorMismatchError,
    verify_ledger_tip_against_anchor,
)
from praetor.state.sqlite_guard import critical_transaction


def test_tip_anchor_skipped_when_anchor_is_none(conn: sqlite3.Connection) -> None:
    verify_ledger_tip_against_anchor(conn, expected_tip_hash=None)


def test_tip_anchor_matches_live_tip(conn: sqlite3.Connection) -> None:
    with critical_transaction(conn):
        append_ledger_record(conn, sample_decision_edict())
    conn.commit()
    tip = fetch_ledger_tip_hash(conn)
    assert tip is not None
    verify_ledger_tip_against_anchor(conn, expected_tip_hash=tip)


def test_tip_anchor_mismatch_raises(conn: sqlite3.Connection) -> None:
    with critical_transaction(conn):
        append_ledger_record(conn, sample_decision_edict())
    conn.commit()
    with pytest.raises(LedgerTipAnchorMismatchError, match="operator-supplied anchor"):
        verify_ledger_tip_against_anchor(conn, expected_tip_hash="deadbeef" * 8)


def test_tip_anchor_mismatch_is_chain_integrity_error(
    conn: sqlite3.Connection,
) -> None:
    with critical_transaction(conn):
        append_ledger_record(conn, sample_decision_edict())
    conn.commit()
    with pytest.raises(LedgerChainIntegrityError):
        verify_ledger_tip_against_anchor(conn, expected_tip_hash="0" * 64)


def test_empty_ledger_anchor_mismatch(conn: sqlite3.Connection) -> None:
    with pytest.raises(LedgerTipAnchorMismatchError):
        verify_ledger_tip_against_anchor(conn, expected_tip_hash="0" * 64)
