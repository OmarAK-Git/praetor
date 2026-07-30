"""Coverage for annotations.precedent malformed-edict visibility (DEBT-022)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from praetor.annotations.precedent import fetch_human_confirmed_precedents
from praetor.annotations.store import init_annotation_schema, submit_annotation
from praetor.auth import Principal, PrincipalMapVerifier
from praetor.ledger.hash_chain import DECISION_EDICT_RECORD_TYPE
from praetor.state.sqlite_guard import create_guarded_connection, critical_transaction
from praetor.state.store import init_state_schema

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
ANALYST_TOKEN = "token-analyst"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[Any]:
    from praetor.alerts.outbox import init_health_alert_outbox_schema
    from praetor.state.sqlite_guard import init_state_dir
    from praetor.tickets.outbox import init_stamp_outbox_schema

    db_path = tmp_path / "state.db"
    init_state_dir(db_path)
    connection = create_guarded_connection(db_path)
    import sqlite3

    connection.row_factory = sqlite3.Row
    init_state_schema(connection)
    init_stamp_outbox_schema(connection)
    init_health_alert_outbox_schema(connection)
    init_annotation_schema(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_chain (
            sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_json TEXT NOT NULL
        )
        """
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {ANALYST_TOKEN: Principal(identity="analyst@example.com", role="analyst")}
    )


def test_fetch_human_confirmed_precedents_logs_and_skips_malformed_edict(
    conn: Any, verifier: PrincipalMapVerifier, caplog: pytest.LogCaptureFixture
) -> None:
    decision_id = "dec-corrupt"
    corrupt_json = '{"decision_id": "dec-corrupt", "not_a_valid": "edict"}'
    conn.execute(
        "INSERT INTO ledger_chain (record_type, record_json) VALUES (?, ?)",
        (DECISION_EDICT_RECORD_TYPE, corrupt_json),
    )
    conn.commit()
    with critical_transaction(conn):
        submit_annotation(
            conn,
            token=ANALYST_TOKEN,
            verifier=verifier,
            decision_id=decision_id,
            disposition_correct=True,
            corrected_disposition=None,
            comment="looks right",
            timestamp=NOW,
        )
    conn.commit()

    with caplog.at_level("WARNING", logger="praetor.annotations.precedent"):
        precedents = fetch_human_confirmed_precedents(conn)

    assert precedents == []
    assert any(
        "malformed ledger edict" in record.message and decision_id in record.message
        for record in caplog.records
    )
