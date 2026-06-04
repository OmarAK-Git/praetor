"""Task 10 — startup ledger chain integrity verification."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from tests.ledger.conftest import sample_decision_edict

from praetor.alerts.outbox import fetch_health_alert_outbox
from praetor.ledger.hash_chain import LedgerChainIntegrityError
from praetor.ledger.startup import (
    LEDGER_CHAIN_INTEGRITY_ALERT_CODE,
    LedgerStartupError,
    run_ledger_startup_hook,
    verify_ledger_chain_at_startup,
)
from praetor.ledger.store import append_ledger_record
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import open_state_store


def test_startup_empty_chain_passes(conn: sqlite3.Connection) -> None:
    verify_ledger_chain_at_startup(conn, emit_health_alert=False)
    conn.commit()


def test_startup_valid_chain_passes(conn: sqlite3.Connection) -> None:
    with critical_transaction(conn):
        append_ledger_record(conn, sample_decision_edict())
    verify_ledger_chain_at_startup(conn, emit_health_alert=False)
    conn.commit()


def test_startup_tampered_chain_emits_alert_and_refuses(
    conn: sqlite3.Connection,
) -> None:
    with critical_transaction(conn):
        append_ledger_record(conn, sample_decision_edict())
    conn.commit()

    conn.execute(
        """
        UPDATE ledger_chain
        SET ledger_current_hash = 'tampered'
        WHERE chain_sequence = 1
        """
    )
    conn.commit()

    with pytest.raises(LedgerStartupError) as exc_info:
        verify_ledger_chain_at_startup(conn, emit_health_alert=True)
    assert exc_info.value.exit_code != 0
    assert isinstance(exc_info.value.__cause__, LedgerChainIntegrityError)

    row = conn.execute(
        """
        SELECT alert_id FROM system_health_alert_outbox
        ORDER BY created_at DESC LIMIT 1
        """
    ).fetchone()
    assert row is not None
    outbox = fetch_health_alert_outbox(conn, str(row["alert_id"]))
    assert outbox is not None
    assert outbox.alert.alert_code == LEDGER_CHAIN_INTEGRITY_ALERT_CODE


def test_open_state_store_inits_ledger_schema(db_path: Path) -> None:
    store = open_state_store(db_path)
    try:
        row = store.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'ledger_chain'
            """
        ).fetchone()
        assert row is not None
    finally:
        store.close()


def test_open_state_store_runs_ledger_startup_hook(db_path: Path) -> None:
    store = open_state_store(db_path)
    try:
        with critical_transaction(store.conn):
            append_ledger_record(store.conn, sample_decision_edict())
        store.conn.commit()
        store.close()

        store = open_state_store(db_path)
        row = store.conn.execute("SELECT COUNT(*) FROM ledger_chain").fetchone()
        assert row is not None
        assert int(row[0]) == 1
    finally:
        store.close()


def test_open_state_store_refuses_tampered_ledger(db_path: Path) -> None:
    store = open_state_store(db_path)
    try:
        with critical_transaction(store.conn):
            append_ledger_record(store.conn, sample_decision_edict())
        store.conn.commit()
    finally:
        store.close()

    import sqlite3

    raw = sqlite3.connect(db_path)
    raw.execute(
        """
        UPDATE ledger_chain
        SET ledger_current_hash = 'tampered'
        WHERE chain_sequence = 1
        """
    )
    raw.commit()
    raw.close()

    with pytest.raises(LedgerStartupError):
        open_state_store(db_path)

    raw = sqlite3.connect(db_path)
    raw.row_factory = sqlite3.Row
    alert_row = raw.execute(
        "SELECT alert_code FROM system_health_alert_outbox ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    raw.close()
    assert alert_row is not None
    assert alert_row["alert_code"] == LEDGER_CHAIN_INTEGRITY_ALERT_CODE


def test_run_ledger_startup_hook_commits_alert_on_failure(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        INSERT INTO ledger_chain (
            record_type, record_json, ledger_previous_hash, ledger_current_hash
        ) VALUES (?, ?, NULL, ?)
        """,
        (
            "decision_edict",
            '{"schema_version":"1","record_type":"decision_edict"}',
            "badhash",
        ),
    )
    conn.commit()

    with pytest.raises(LedgerStartupError):
        run_ledger_startup_hook(conn)

    alert_row = conn.execute(
        "SELECT COUNT(*) FROM system_health_alert_outbox"
    ).fetchone()
    assert alert_row is not None
    assert int(alert_row[0]) == 1
