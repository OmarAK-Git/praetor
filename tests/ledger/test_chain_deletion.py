"""Task 10 — chain deletion/truncation detection boundaries."""

from __future__ import annotations

import sqlite3

import pytest
from tests.ledger.conftest import sample_decision_edict

from praetor.ledger.hash_chain import LedgerChainIntegrityError, verify_ledger_chain
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import critical_transaction


def _append_three(conn: sqlite3.Connection) -> None:
    for idx in range(3):
        with critical_transaction(conn):
            append_ledger_record(conn, sample_decision_edict(decision_id=f"dec-{idx}"))
    conn.commit()


def test_middle_deletion_breaks_chain(conn: sqlite3.Connection) -> None:
    _append_three(conn)
    conn.execute("DELETE FROM ledger_chain WHERE chain_sequence = 2")
    conn.commit()

    with pytest.raises(LedgerChainIntegrityError, match="broken chain"):
        verify_ledger_chain(conn)


def test_tail_truncation_may_verify(conn: sqlite3.Connection) -> None:
    """Tail deletion is not detectable without an external anchored tip (§7a)."""
    _append_three(conn)
    conn.execute("DELETE FROM ledger_chain WHERE chain_sequence = 3")
    conn.commit()

    verify_ledger_chain(conn)
