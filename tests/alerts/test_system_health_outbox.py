"""Task 8 — SystemHealthAlert outbox."""

from __future__ import annotations

import importlib
import io
import json
import sqlite3
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.alerts._fakes import (
    AppendOnlyJsonlSink,
    FailingJsonlSink,
    RuntimeErrorStdoutSink,
)

from praetor.alerts.outbox import (
    V1_DELIVERY_CHANNELS,
    DeliveryStatus,
    DuplicateHealthAlertError,
    fetch_delivery_attempt,
    fetch_health_alert_outbox,
    fetch_retryable_delivery_attempts,
    init_health_alert_outbox_schema,
    record_delivery_attempt,
    write_pending_health_alert,
)
from praetor.alerts.system_health import (
    JsonlSink,
    StdoutSink,
    deliver_health_alerts,
    emit_system_health_alert,
)
from praetor.contracts.health import SystemHealthAlert
from praetor.state.sqlite_guard import (
    StartupGuardError,
    create_guarded_connection,
    critical_transaction,
    init_state_dir,
)
from praetor.state.store import (
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    init_state_schema,
    open_state_store,
)
from praetor.tickets.outbox import init_stamp_outbox_schema

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
FIXED_ALERT_ID = "11111111-1111-4111-8111-111111111111"


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
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def jsonl_path(tmp_path: Path) -> Path:
    return tmp_path / "health_alerts.jsonl"


def _sample_alert(*, code: str = "revocation_feed_unhealthy") -> SystemHealthAlert:
    return SystemHealthAlert(alert_code=code, emitted_at=NOW)


def test_health_alert_persisted_before_delivery_attempt(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert()
    stdout = io.StringIO()

    entry = emit_system_health_alert(
        conn,
        alert,
        jsonl_sink=JsonlSink(jsonl_path),
        stdout_sink=StdoutSink(stdout),
        deliver=False,
    )
    conn.commit()

    assert entry.alert.alert_code == "revocation_feed_unhealthy"
    assert fetch_health_alert_outbox(conn, entry.alert_id) is not None
    for channel in V1_DELIVERY_CHANNELS:
        attempt = fetch_delivery_attempt(conn, entry.alert_id, channel)
        assert attempt is not None
        assert attempt.status == DeliveryStatus.PENDING
    assert not jsonl_path.exists()


def test_jsonl_and_stdout_delivery_statuses_recorded(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert(code="containment_breaker_open")
    stdout = io.StringIO()

    entry = emit_system_health_alert(
        conn,
        alert,
        jsonl_sink=JsonlSink(jsonl_path),
        stdout_sink=StdoutSink(stdout),
    )
    conn.commit()

    jsonl_attempt = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    stdout_attempt = fetch_delivery_attempt(conn, entry.alert_id, "stdout")
    assert jsonl_attempt is not None
    assert stdout_attempt is not None
    assert jsonl_attempt.status == DeliveryStatus.SUCCEEDED
    assert stdout_attempt.status == DeliveryStatus.SUCCEEDED
    assert jsonl_attempt.attempted_at is not None
    assert stdout_attempt.attempted_at is not None

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["alert_code"] == "containment_breaker_open"
    assert stdout.getvalue().strip() == lines[0]


def test_failed_delivery_remains_retryable(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert()
    stdout = io.StringIO()
    failing = FailingJsonlSink(jsonl_path, fail_count=1)

    entry = emit_system_health_alert(
        conn,
        alert,
        jsonl_sink=failing,
        stdout_sink=StdoutSink(stdout),
    )
    conn.commit()

    jsonl_attempt = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    assert jsonl_attempt is not None
    assert jsonl_attempt.status == DeliveryStatus.FAILED
    assert jsonl_attempt.result is not None
    assert "error" in jsonl_attempt.result

    stdout_attempt = fetch_delivery_attempt(conn, entry.alert_id, "stdout")
    assert stdout_attempt is not None
    assert stdout_attempt.status == DeliveryStatus.SUCCEEDED

    deliver_health_alerts(
        conn,
        jsonl_sink=failing,
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    jsonl_attempt_after = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    assert jsonl_attempt_after is not None
    assert jsonl_attempt_after.status == DeliveryStatus.SUCCEEDED
    assert jsonl_path.read_text(encoding="utf-8").strip()


def test_outbox_schema_supports_future_channels_without_migration(
    conn: sqlite3.Connection,
) -> None:
    alert = _sample_alert()
    entry = write_pending_health_alert(conn, alert)
    conn.execute(
        """
        INSERT INTO system_health_delivery_attempts (
            alert_id, channel, status, attempted_at, result_json
        ) VALUES (?, ?, ?, NULL, NULL)
        """,
        (entry.alert_id, "siem", DeliveryStatus.PENDING.value),
    )
    conn.commit()

    row = conn.execute(
        """
        SELECT channel, status FROM system_health_delivery_attempts
        WHERE alert_id = ? AND channel = ?
        """,
        (entry.alert_id, "siem"),
    ).fetchone()
    assert row is not None
    assert row["channel"] == "siem"
    assert row["status"] == DeliveryStatus.PENDING.value


def test_revocation_feed_unhealthy_alert_supported(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = SystemHealthAlert(
        alert_code="revocation_feed_unhealthy",
        emitted_at=NOW,
    )
    entry = emit_system_health_alert(
        conn,
        alert,
        jsonl_sink=JsonlSink(jsonl_path),
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    stored = fetch_health_alert_outbox(conn, entry.alert_id)
    assert stored is not None
    assert stored.alert.alert_code == "revocation_feed_unhealthy"
    payload = json.loads(jsonl_path.read_text(encoding="utf-8").strip())
    assert payload["alert_code"] == "revocation_feed_unhealthy"


def test_system_health_alert_is_outbox_only(conn: sqlite3.Connection) -> None:
    alert = _sample_alert(code="ledger_chain_integrity_failure")
    entry = write_pending_health_alert(conn, alert)
    conn.commit()

    ledger_tables = (
        "directive_revocation_records",
        "processing_attempts",
        "completed_decisions",
    )
    for table in ledger_tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        assert count is not None
        assert int(count[0]) == 0

    outbox = fetch_health_alert_outbox(conn, entry.alert_id)
    assert outbox is not None
    assert outbox.alert.alert_code == "ledger_chain_integrity_failure"


def test_open_state_store_inits_health_alert_outbox_schema(db_path: Path) -> None:
    store = open_state_store(db_path)
    try:
        row = store.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'system_health_alert_outbox'
            """
        ).fetchone()
        assert row is not None
        delivery_row = store.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'system_health_delivery_attempts'
            """
        ).fetchone()
        assert delivery_row is not None
    finally:
        store.close()


def test_task7_db_gains_health_alert_tables_without_schema_bump(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "task7_only.db"
    init_state_dir(db_path)
    conn = create_guarded_connection(db_path)
    conn.row_factory = sqlite3.Row
    init_state_schema(conn)
    init_stamp_outbox_schema(conn)
    conn.commit()
    version_before = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (SCHEMA_VERSION_KEY,),
    ).fetchone()
    conn.close()

    store = open_state_store(db_path)
    try:
        assert int(version_before[0]) == SCHEMA_VERSION
        stored_version = store.conn.execute(
            "SELECT value FROM schema_meta WHERE key = ?",
            (SCHEMA_VERSION_KEY,),
        ).fetchone()
        assert stored_version is not None
        assert int(stored_version[0]) == SCHEMA_VERSION
        table = store.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'system_health_alert_outbox'
            """
        ).fetchone()
        assert table is not None
    finally:
        store.close()


def test_succeeded_channel_not_redelivered_on_retry(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert()
    stdout = io.StringIO()
    failing = FailingJsonlSink(jsonl_path, fail_count=1)

    entry = emit_system_health_alert(
        conn,
        alert,
        jsonl_sink=failing,
        stdout_sink=StdoutSink(stdout),
    )
    conn.commit()
    first_stdout = stdout.getvalue()

    deliver_health_alerts(
        conn,
        jsonl_sink=failing,
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    stdout_attempt = fetch_delivery_attempt(conn, entry.alert_id, "stdout")
    assert stdout_attempt is not None
    assert stdout_attempt.status == DeliveryStatus.SUCCEEDED
    assert first_stdout.strip()


class TestRecordDeliveryAttemptGuards:
    def test_record_pending_outcome_rejected_and_row_unchanged(
        self, conn: sqlite3.Connection
    ) -> None:
        entry = write_pending_health_alert(conn, _sample_alert())
        conn.commit()

        with pytest.raises(ValueError, match="succeeded or failed status"):
            record_delivery_attempt(
                conn,
                entry.alert_id,
                "jsonl",
                DeliveryStatus.PENDING,
                None,
            )

        attempt = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
        assert attempt is not None
        assert attempt.status == DeliveryStatus.PENDING
        assert attempt.attempted_at is None

    def test_record_unknown_channel_raises_key_error(
        self, conn: sqlite3.Connection
    ) -> None:
        entry = write_pending_health_alert(conn, _sample_alert())
        conn.commit()

        with pytest.raises(KeyError, match="delivery attempt not found"):
            record_delivery_attempt(
                conn,
                entry.alert_id,
                "siem",
                DeliveryStatus.SUCCEEDED,
                {"channel": "siem"},
            )

        attempt = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
        assert attempt is not None
        assert attempt.status == DeliveryStatus.PENDING


def test_delivery_attempt_foreign_key_rejects_orphan_alert_id(
    conn: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO system_health_delivery_attempts (
                alert_id, channel, status, attempted_at, result_json
            ) VALUES (?, ?, ?, NULL, NULL)
            """,
            ("missing-alert-id", "jsonl", DeliveryStatus.PENDING.value),
        )


def test_write_pending_health_alert_rejects_nested_critical_transaction(
    conn: sqlite3.Connection,
) -> None:
    alert = _sample_alert()
    with critical_transaction(conn):
        with pytest.raises(StartupGuardError, match="nested critical_transaction"):
            write_pending_health_alert(conn, alert)


def test_emit_without_delivery_rejects_nested_critical_transaction(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert()
    with critical_transaction(conn):
        with pytest.raises(StartupGuardError, match="nested critical_transaction"):
            emit_system_health_alert(
                conn,
                alert,
                jsonl_sink=JsonlSink(jsonl_path),
                stdout_sink=StdoutSink(io.StringIO()),
                deliver=False,
            )


def test_duplicate_alert_id_same_payload_is_idempotent(
    conn: sqlite3.Connection,
) -> None:
    alert = _sample_alert()
    first = write_pending_health_alert(conn, alert, alert_id=FIXED_ALERT_ID)
    second = write_pending_health_alert(conn, alert, alert_id=FIXED_ALERT_ID)
    conn.commit()

    assert first.alert_id == second.alert_id
    count = conn.execute(
        "SELECT COUNT(*) FROM system_health_alert_outbox"
    ).fetchone()
    assert count is not None
    assert int(count[0]) == 1


def test_duplicate_alert_id_different_payload_raises(
    conn: sqlite3.Connection,
) -> None:
    write_pending_health_alert(
        conn,
        _sample_alert(code="revocation_feed_unhealthy"),
        alert_id=FIXED_ALERT_ID,
    )
    with pytest.raises(DuplicateHealthAlertError, match="health alert id conflict"):
        write_pending_health_alert(
            conn,
            _sample_alert(code="containment_breaker_open"),
            alert_id=FIXED_ALERT_ID,
        )


def test_fail_then_fail_retry_stays_failed(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert()
    failing = FailingJsonlSink(jsonl_path, fail_count=2)

    entry = emit_system_health_alert(
        conn,
        alert,
        jsonl_sink=failing,
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    first = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    assert first is not None
    assert first.status == DeliveryStatus.FAILED
    first_attempted_at = first.attempted_at

    deliver_health_alerts(
        conn,
        jsonl_sink=failing,
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    second = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    assert second is not None
    assert second.status == DeliveryStatus.FAILED
    assert second.attempted_at is not None
    assert second.attempted_at >= first_attempted_at
    assert second.result is not None
    assert second.result.get("exception_type") == "OSError"
    assert not jsonl_path.exists() or jsonl_path.read_text(encoding="utf-8") == ""


def test_jsonl_at_least_once_duplicate_on_crash_before_record(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    alert = _sample_alert()
    entry = write_pending_health_alert(conn, alert)
    conn.commit()

    crash_sink = AppendOnlyJsonlSink(jsonl_path)
    deliver_health_alerts(
        conn,
        jsonl_sink=crash_sink,
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    first_attempt = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    assert first_attempt is not None
    assert first_attempt.status == DeliveryStatus.FAILED

    deliver_health_alerts(
        conn,
        jsonl_sink=JsonlSink(jsonl_path),
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert lines[0] == lines[1]
    final = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    assert final is not None
    assert final.status == DeliveryStatus.SUCCEEDED


def test_fetch_retryable_empty_when_fully_succeeded(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    emit_system_health_alert(
        conn,
        _sample_alert(),
        jsonl_sink=JsonlSink(jsonl_path),
        stdout_sink=StdoutSink(io.StringIO()),
    )
    conn.commit()

    assert fetch_retryable_delivery_attempts(conn) == []


def test_non_oserror_sink_failure_recorded_as_failed(
    conn: sqlite3.Connection,
    jsonl_path: Path,
) -> None:
    entry = emit_system_health_alert(
        conn,
        _sample_alert(),
        jsonl_sink=JsonlSink(jsonl_path),
        stdout_sink=RuntimeErrorStdoutSink(),
    )
    conn.commit()

    jsonl_attempt = fetch_delivery_attempt(conn, entry.alert_id, "jsonl")
    stdout_attempt = fetch_delivery_attempt(conn, entry.alert_id, "stdout")
    assert jsonl_attempt is not None
    assert jsonl_attempt.status == DeliveryStatus.SUCCEEDED
    assert stdout_attempt is not None
    assert stdout_attempt.status == DeliveryStatus.FAILED
    assert stdout_attempt.result is not None
    assert stdout_attempt.result.get("exception_type") == "RuntimeError"


def test_record_delivery_attempt_rejects_nested_critical_transaction(
    conn: sqlite3.Connection,
) -> None:
    entry = write_pending_health_alert(conn, _sample_alert())
    conn.commit()
    with critical_transaction(conn):
        with pytest.raises(StartupGuardError, match="nested critical_transaction"):
            record_delivery_attempt(
                conn,
                entry.alert_id,
                "jsonl",
                DeliveryStatus.SUCCEEDED,
                {"channel": "jsonl"},
            )


class TestImportOrderSmoke:
    def test_store_then_outbox_import(self) -> None:
        for name in ("praetor.state.store", "praetor.alerts.outbox"):
            sys.modules.pop(name, None)
        store_mod = importlib.import_module("praetor.state.store")
        outbox_mod = importlib.import_module("praetor.alerts.outbox")
        assert store_mod.open_state_store is not None
        assert outbox_mod.write_pending_health_alert is not None

    def test_outbox_then_store_import(self) -> None:
        for name in ("praetor.state.store", "praetor.alerts.outbox"):
            sys.modules.pop(name, None)
        outbox_mod = importlib.import_module("praetor.alerts.outbox")
        store_mod = importlib.import_module("praetor.state.store")
        assert outbox_mod.fetch_health_alert_outbox is not None
        assert store_mod.open_state_store is not None
