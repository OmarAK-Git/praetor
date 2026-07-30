"""Task 11 — revocation feed exporter and outbox."""

from __future__ import annotations

import ast
import inspect
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.hashing.domains import compute_feed_record_checksum
from praetor.revocation.exporter import (
    FileFeedJsonlSink,
    export_next_pending_row,
    export_pending_feed_rows,
    is_feed_actuation_blocked,
    reconcile_feed_metadata_against_jsonl,
    run_feed_startup_hook,
)
from praetor.revocation.feed import (
    FeedChecksumError,
    build_feed_record,
    feed_record_to_jsonl_line,
    verify_feed_jsonl_line,
)
from praetor.revocation.outbox import (
    is_feed_unhealthy,
    mark_feed_row_exported,
    oldest_pending_feed_age_seconds,
    read_last_verified_exported_sequence,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import (
    StateStore,
    fetch_feed_outbox_row,
    fetch_revocation_record_json,
    open_state_store,
)


def _revocation(
    *,
    revocation_id: str,
    ledger_commit_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> DirectiveRevocationRecord:
    now = datetime.now(UTC)
    commit = ledger_commit_at if ledger_commit_at is not None else now
    revoked = revoked_at if revoked_at is not None else now
    return DirectiveRevocationRecord(
        revocation_id=revocation_id,
        directive_id="dir-1",
        reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
        reason_code="never_contain_conflict",
        triggered_by="test",
        revoked_at=revoked,
        ledger_commit_at=commit,
        idempotency_key_cleared=False,
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    s = open_state_store(db)
    yield s
    s.close()


@pytest.fixture
def feed_path(tmp_path: Path) -> Path:
    return tmp_path / "revocation_feed.jsonl"


class FailingFeedSink:
    def append_line(self, line: str) -> None:
        raise OSError("injected export failure")


class FlakyFeedSink:
    def __init__(self, path: Path, *, fail_count: int) -> None:
        self.path = path
        self.fail_count = fail_count
        self.attempts = 0

    def append_line(self, line: str) -> None:
        if self.attempts < self.fail_count:
            self.attempts += 1
            raise OSError("transient failure")
        sink = FileFeedJsonlSink(self.path)
        sink.append_line(line)


class TestRevocationTransaction:
    def test_revocation_transaction_assigns_sequence_and_outbox(
        self, store: StateStore
    ) -> None:
        first = store.write_automated_revocation(_revocation(revocation_id="rev-a"))
        second = store.write_automated_revocation(_revocation(revocation_id="rev-b"))
        assert first.sequence_number == 1
        assert second.sequence_number == 2
        row = fetch_feed_outbox_row(store.conn, 2)
        assert row is not None
        assert row["status"] == "pending"


class TestFeedExporter:
    def test_exporter_writes_rows_in_sequence_order(
        self, store: StateStore, feed_path: Path
    ) -> None:
        for index in range(3):
            store.write_automated_revocation(
                _revocation(revocation_id=f"rev-seq-{index}")
            )
        sink = FileFeedJsonlSink(feed_path)
        result = export_pending_feed_rows(
            store.conn, sink=sink, max_feed_export_retries=3
        )
        assert result.exported_count == 3
        lines = feed_path.read_text(encoding="utf-8").strip().splitlines()
        sequences = [json.loads(line)["sequence_number"] for line in lines]
        assert sequences == [1, 2, 3]

    def test_record_checksum_verifies_after_write(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-chk"))
        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        line = feed_path.read_text(encoding="utf-8").strip()
        record = verify_feed_jsonl_line(line)
        assert record.sequence_number == 1
        raw = fetch_revocation_record_json(store.conn, "rev-chk")
        assert raw is not None
        source = DirectiveRevocationRecord.model_validate_json(raw)
        rebuilt = build_feed_record(source, sequence_number=1)
        assert rebuilt.record_checksum == record.record_checksum

    def test_export_retry_respects_max_retries(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-retry"))
        sink = FlakyFeedSink(feed_path, fail_count=2)
        assert export_next_pending_row(
            store.conn, sink=sink, max_feed_export_retries=3
        ) is False
        assert export_next_pending_row(
            store.conn, sink=sink, max_feed_export_retries=3
        ) is False
        assert export_next_pending_row(
            store.conn, sink=sink, max_feed_export_retries=3
        ) is True
        assert read_last_verified_exported_sequence(store.conn) == 1

    def test_retry_exhaustion_marks_unhealthy_and_alerts(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-exhaust"))
        sink = FailingFeedSink()
        for _ in range(3):
            export_next_pending_row(
                store.conn, sink=sink, max_feed_export_retries=3
            )
        assert is_feed_actuation_blocked(
            store.conn, propagation_delay_seconds=60
        )
        row = store.conn.execute(
            """
            SELECT alert_code FROM system_health_alert_outbox
            WHERE alert_code = ?
            """,
            ("revocation_feed_unhealthy",),
        ).fetchone()
        assert row is not None

    def test_oldest_pending_age_from_ledger_commit_at(
        self, store: StateStore
    ) -> None:
        old_commit = datetime.now(UTC) - timedelta(seconds=120)
        store.write_automated_revocation(
            _revocation(revocation_id="rev-old", ledger_commit_at=old_commit)
        )
        age = oldest_pending_feed_age_seconds(store.conn)
        assert age is not None
        assert age >= 120.0

    def test_checksum_verification_failure_is_hard_unhealthy(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-hard-fail"))
        with patch(
            "praetor.revocation.exporter.verify_feed_jsonl_line",
            side_effect=FeedChecksumError("post-write verification failed"),
        ):
            export_next_pending_row(
                store.conn,
                sink=FileFeedJsonlSink(feed_path),
                max_feed_export_retries=3,
            )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0
        retry_row = store.conn.execute(
            """
            SELECT export_retry_count FROM revocation_feed_outbox
            WHERE sequence_number = 1
            """
        ).fetchone()
        assert retry_row is not None
        assert int(retry_row[0]) == 0
        alert = store.conn.execute(
            """
            SELECT alert_code FROM system_health_alert_outbox
            WHERE alert_code = ?
            """,
            ("revocation_feed_unhealthy",),
        ).fetchone()
        assert alert is not None

    def test_crash_recovery_marks_exported_without_duplicate_jsonl_line(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-crash"))
        raw = fetch_revocation_record_json(store.conn, "rev-crash")
        assert raw is not None
        source = DirectiveRevocationRecord.model_validate_json(raw)
        feed = build_feed_record(source, sequence_number=1)
        feed_path.write_text(feed_record_to_jsonl_line(feed) + "\n", encoding="utf-8")
        assert fetch_feed_outbox_row(store.conn, 1)["status"] == "pending"

        assert export_next_pending_row(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        lines = feed_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        verify_feed_jsonl_line(lines[0])
        assert read_last_verified_exported_sequence(store.conn) == 1
        assert fetch_feed_outbox_row(store.conn, 1)["status"] == "exported"

        run_feed_startup_hook(
            store.conn,
            feed_path=feed_path,
            max_feed_export_retries=3,
            propagation_delay_seconds=60,
        )
        assert len(feed_path.read_text(encoding="utf-8").strip().splitlines()) == 1

    def test_unhealthy_feed_recovers_when_export_succeeds(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-recover"))
        for _ in range(3):
            export_next_pending_row(
                store.conn, sink=FailingFeedSink(), max_feed_export_retries=3
            )
        assert is_feed_unhealthy(store.conn)
        assert export_next_pending_row(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert not is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 1
        assert not is_feed_actuation_blocked(
            store.conn, propagation_delay_seconds=60
        )

    def test_sequence_gap_marks_unhealthy_and_alerts(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-gap-1"))
        store.write_automated_revocation(_revocation(revocation_id="rev-gap-2"))
        store.conn.execute(
            "DELETE FROM revocation_feed_outbox WHERE sequence_number = 1"
        )
        store.conn.commit()
        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0
        alert = store.conn.execute(
            """
            SELECT alert_code FROM system_health_alert_outbox
            WHERE alert_code = ?
            """,
            ("revocation_feed_unhealthy",),
        ).fetchone()
        assert alert is not None

    def test_canonical_timestamps_zero_microseconds_and_non_utc_offset(
        self, store: StateStore, feed_path: Path
    ) -> None:
        zero_utc = datetime(2026, 6, 1, 12, 0, 0, 0, tzinfo=UTC)
        eastern = datetime(2026, 6, 1, 8, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        store.write_automated_revocation(
            _revocation(
                revocation_id="rev-ts",
                revoked_at=zero_utc,
                ledger_commit_at=eastern,
            )
        )
        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        line = feed_path.read_text(encoding="utf-8").strip()
        assert "2026-06-01T12:00:00.000000Z" in line
        record = verify_feed_jsonl_line(line)
        raw = fetch_revocation_record_json(store.conn, "rev-ts")
        assert raw is not None
        source = DirectiveRevocationRecord.model_validate_json(raw)
        assert build_feed_record(source, sequence_number=1).record_checksum == (
            record.record_checksum
        )

    def test_recovery_rejects_projection_mismatch_with_valid_checksum(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-mismatch"))
        raw = fetch_revocation_record_json(store.conn, "rev-mismatch")
        assert raw is not None
        source = DirectiveRevocationRecord.model_validate_json(raw)
        authoritative = build_feed_record(source, sequence_number=1)
        mismatched_body = {
            key: value
            for key, value in authoritative.model_dump(mode="python").items()
            if key != "record_checksum"
        }
        mismatched_body["reason_code"] = "wrong_reason_code"
        checksum = compute_feed_record_checksum(mismatched_body)
        mismatched = RevocationFeedRecord(
            **mismatched_body,
            record_checksum=checksum,
        )
        feed_path.write_text(
            feed_record_to_jsonl_line(mismatched) + "\n", encoding="utf-8"
        )

        assert not export_next_pending_row(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0
        assert fetch_feed_outbox_row(store.conn, 1)["status"] == "pending"

    def test_corrupt_feed_prefix_blocks_export_and_health_recovery(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-bad-prefix"))
        store.write_automated_revocation(_revocation(revocation_id="rev-good-next"))
        feed_path.write_text("{not-json\n", encoding="utf-8")

        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0
        assert fetch_feed_outbox_row(store.conn, 1)["status"] == "pending"
        assert fetch_feed_outbox_row(store.conn, 2)["status"] == "pending"
        assert feed_path.read_text(encoding="utf-8").strip() == "{not-json"

    def test_duplicate_sequence_in_feed_prefix_marks_unhealthy(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-dup"))
        raw = fetch_revocation_record_json(store.conn, "rev-dup")
        assert raw is not None
        source = DirectiveRevocationRecord.model_validate_json(raw)
        line = feed_record_to_jsonl_line(build_feed_record(source, sequence_number=1))
        feed_path.write_text(line + "\n" + line + "\n", encoding="utf-8")

        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0

    def test_out_of_order_feed_prefix_marks_unhealthy(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-oo-1"))
        store.write_automated_revocation(_revocation(revocation_id="rev-oo-2"))
        raw1 = fetch_revocation_record_json(store.conn, "rev-oo-1")
        raw2 = fetch_revocation_record_json(store.conn, "rev-oo-2")
        assert raw1 is not None and raw2 is not None
        line2 = feed_record_to_jsonl_line(
            build_feed_record(
                DirectiveRevocationRecord.model_validate_json(raw2),
                sequence_number=2,
            )
        )
        line1 = feed_record_to_jsonl_line(
            build_feed_record(
                DirectiveRevocationRecord.model_validate_json(raw1),
                sequence_number=1,
            )
        )
        feed_path.write_text(line2 + "\n" + line1 + "\n", encoding="utf-8")

        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0

    def test_missing_feed_file_when_metadata_claims_exported_marks_unhealthy(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-meta-gap"))
        with critical_transaction(store.conn):
            mark_feed_row_exported(store.conn, sequence_number=1)
        store.conn.commit()
        if feed_path.exists():
            feed_path.unlink()

        export_next_pending_row(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 1
        assert is_feed_actuation_blocked(
            store.conn, propagation_delay_seconds=60
        )

    def test_truncated_feed_prefix_when_metadata_claims_exported(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-trunc-1"))
        store.write_automated_revocation(_revocation(revocation_id="rev-trunc-2"))
        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert read_last_verified_exported_sequence(store.conn) == 2
        lines = feed_path.read_text(encoding="utf-8").strip().splitlines()
        feed_path.write_text(lines[0] + "\n", encoding="utf-8")

        export_next_pending_row(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)

    def test_schema_invalid_json_line_marks_unhealthy_not_crash(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-schema"))
        partial = {
            "schema_version": "2",
            "sequence_number": 1,
            "directive_id": "dir-1",
            "revocation_id": "rev-schema",
            "reason_code": "never_contain_conflict",
            "revoked_at": "2026-06-01T12:00:00.000000Z",
            "ledger_commit_at": "2026-06-01T12:00:00.000000Z",
        }
        checksum = compute_feed_record_checksum(partial)
        partial["record_checksum"] = checksum
        feed_path.write_text(json.dumps(partial) + "\n", encoding="utf-8")

        export_pending_feed_rows(
            store.conn, sink=FileFeedJsonlSink(feed_path), max_feed_export_retries=3
        )
        assert is_feed_unhealthy(store.conn)
        assert read_last_verified_exported_sequence(store.conn) == 0
        assert fetch_feed_outbox_row(store.conn, 1)["status"] == "pending"

    def test_feed_jsonl_has_no_rotation_machinery(self) -> None:
        from praetor.revocation import exporter as exporter_module

        source = inspect.getsource(exporter_module)
        tree = ast.parse(source)
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        forbidden = {"rotate", "truncate", "rollover", "archive_feed"}
        assert forbidden.isdisjoint(names)
        assert "open(" in source and "'a'" in source or '"a"' in source

    def test_fresh_db_metadata_floor_is_zero_and_reconciles(
        self, store: StateStore, feed_path: Path
    ) -> None:
        assert read_last_verified_exported_sequence(store.conn) == 0
        assert reconcile_feed_metadata_against_jsonl(store.conn, feed_path)
        assert not is_feed_unhealthy(store.conn)

    def test_reconcile_marks_unhealthy_on_stale_metadata(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-stale-meta"))
        with critical_transaction(store.conn):
            mark_feed_row_exported(store.conn, sequence_number=1)
        store.conn.commit()
        assert not feed_path.exists()

        assert not reconcile_feed_metadata_against_jsonl(store.conn, feed_path)
        assert is_feed_unhealthy(store.conn)
        alert = store.conn.execute(
            """
            SELECT alert_code FROM system_health_alert_outbox
            WHERE alert_code = ?
            """,
            ("revocation_feed_unhealthy",),
        ).fetchone()
        assert alert is not None

    def test_startup_hook_reconciles_before_export(
        self, store: StateStore, feed_path: Path
    ) -> None:
        store.write_automated_revocation(_revocation(revocation_id="rev-startup-rec"))
        with critical_transaction(store.conn):
            mark_feed_row_exported(store.conn, sequence_number=1)
        store.conn.commit()

        result = run_feed_startup_hook(
            store.conn,
            feed_path=feed_path,
            max_feed_export_retries=3,
            propagation_delay_seconds=60,
        )
        assert result.exported_count == 0
        assert result.feed_unhealthy
        assert result.degraded_actuation


def test_run_feed_startup_hook_emits_size_warning_when_threshold_exceeded(
    tmp_path: Path,
) -> None:
    from praetor.revocation.exporter import (
        check_feed_file_size_warning,
        default_feed_jsonl_path,
    )
    from praetor.state.store import open_state_store

    db_path = tmp_path / "state.db"
    store = open_state_store(db_path)
    feed_path = default_feed_jsonl_path(db_path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_bytes(b"x" * 2048)

    warned = check_feed_file_size_warning(
        store.conn, feed_path, warning_bytes=1024
    )
    store.conn.commit()

    assert warned is True
    rows = store.conn.execute(
        "SELECT alert_code FROM system_health_alert_outbox"
    ).fetchall()
    assert any(row["alert_code"] == "revocation_feed_file_size_warning" for row in rows)
    store.close()


def test_check_feed_file_size_warning_no_alert_below_threshold(
    tmp_path: Path,
) -> None:
    from praetor.revocation.exporter import (
        check_feed_file_size_warning,
        default_feed_jsonl_path,
    )
    from praetor.state.store import open_state_store

    db_path = tmp_path / "state.db"
    store = open_state_store(db_path)
    feed_path = default_feed_jsonl_path(db_path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_bytes(b"x" * 100)

    warned = check_feed_file_size_warning(
        store.conn, feed_path, warning_bytes=1024
    )
    store.conn.commit()

    assert warned is False
    rows = store.conn.execute(
        "SELECT alert_code FROM system_health_alert_outbox"
    ).fetchall()
    assert not any(
        row["alert_code"] == "revocation_feed_file_size_warning" for row in rows
    )
    store.close()


def test_run_feed_startup_hook_wires_size_warning_check(
    tmp_path: Path,
) -> None:
    from praetor.revocation.exporter import (
        default_feed_jsonl_path,
        run_feed_startup_hook_for_db,
    )
    from praetor.state.store import open_state_store

    db_path = tmp_path / "state.db"
    store = open_state_store(db_path)
    feed_path = default_feed_jsonl_path(db_path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_bytes(b"\n" * 2048)

    run_feed_startup_hook_for_db(
        store.conn,
        db_path,
        feed_file_size_warning_bytes=1024,
    )

    rows = store.conn.execute(
        "SELECT alert_code FROM system_health_alert_outbox"
    ).fetchall()
    assert any(row["alert_code"] == "revocation_feed_file_size_warning" for row in rows)
    store.close()
