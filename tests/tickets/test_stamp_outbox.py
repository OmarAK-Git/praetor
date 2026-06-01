"""Task 7 — Ticket stamp outbox."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from praetor.hashing import EMPTY_BUNDLE, derive_stamp_id
from praetor.state.sqlite_guard import create_guarded_connection, init_state_dir
from praetor.state.store import (
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    StateStore,
    init_state_schema,
    open_state_store,
)
from praetor.tickets.outbox import (
    StampStatus,
    fetch_stamp_outbox,
    record_stamp_outcome,
    write_pending_stamp,
)
from praetor.tickets.stamp import (
    NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK,
    StampBackendOutcome,
    StampBackendResult,
    StampContext,
    StampTimeoutError,
    execute_stamp,
)


@dataclass
class IdempotentFakeBackend:
    """Ticket receiver that treats repeated stamp_id as idempotent no-ops."""

    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    _stamped: set[str] = field(default_factory=set)

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        self.calls.append((stamp_id, payload))
        if stamp_id in self._stamped:
            return StampBackendResult(
                outcome=StampBackendOutcome.SUCCEEDED,
                payload={"idempotent_replay": True, "stamp_id": stamp_id},
            )
        self._stamped.add(stamp_id)
        return StampBackendResult(
            outcome=StampBackendOutcome.SUCCEEDED,
            payload={"ticket_ref": "INC-1001", "stamp_id": stamp_id},
        )


@dataclass
class FailingFakeBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        return StampBackendResult(
            outcome=StampBackendOutcome.FAILED,
            payload={"error": "ticket_system_rejected", "stamp_id": stamp_id},
        )


@dataclass
class TimeoutFakeBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        raise StampTimeoutError("ticket system did not respond in time")


@dataclass
class ConnectionErrorBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        raise ConnectionError("ticket API unreachable")


@dataclass
class ProgrammerErrorBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        raise ValueError("invalid payload shape in backend adapter")


@dataclass
class StampThenLoseResponseBackend:
    """Backend accepts stamp then loses response — recovery must idempotently replay."""

    inner: IdempotentFakeBackend

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        self.inner.stamp(stamp_id, payload)
        raise StampTimeoutError("response lost after backend accepted stamp")


@dataclass
class MustNotBeCalledBackend:
    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        msg = "backend must not be invoked for cached terminal outcome"
        raise AssertionError(msg)


def _count_outbox_rows(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM ticket_stamp_outbox").fetchone()
    assert row is not None
    return int(row[0])


@pytest.fixture
def task6_only_db(tmp_path: Path) -> Path:
    """Task 6 schema without ticket_stamp_outbox (DEC-022 additive upgrade path)."""
    db_path = tmp_path / "task6_only.db"
    init_state_dir(db_path)
    conn = create_guarded_connection(db_path)
    init_state_schema(conn)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    s = open_state_store(db)
    yield s
    s.close()


def _context(
    *,
    alert: str = "ALERT-007",
    bundle: str = "bundle-hash",
    org: str = "org-hash",
    attempt: str = "1",
    payload: dict[str, Any] | None = None,
) -> StampContext:
    return StampContext(
        alert_identity=alert,
        evidence_bundle_hash=bundle,
        org_config_snapshot_hash=org,
        processing_attempt_identity=attempt,
        ticket_payload=payload or {"summary": "test stamp"},
    )


class TestPendingBeforeExternalCall:
    def test_pending_outbox_written_before_backend_invoked(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )
        backend = MagicMock()
        backend.stamp.side_effect = lambda sid, payload: (
            _assert_pending_exists(store.conn, sid),
            StampBackendResult(
                outcome=StampBackendOutcome.SUCCEEDED,
                payload={"ticket_ref": "INC-1"},
            ),
        )[1]

        execute_stamp(store.conn, backend, ctx)

        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.status == StampStatus.SUCCEEDED
        backend.stamp.assert_called_once()


def _assert_pending_exists(conn: sqlite3.Connection, stamp_id: str) -> None:
    row = fetch_stamp_outbox(conn, stamp_id)
    assert row is not None
    assert row.status == StampStatus.PENDING


class TestDurableOutcomes:
    def test_success_recorded_durably(self, store: StateStore) -> None:
        ctx = _context()
        backend = IdempotentFakeBackend()

        result = execute_stamp(store.conn, backend, ctx)

        assert result.status == StampStatus.SUCCEEDED
        row = fetch_stamp_outbox(store.conn, result.stamp_id)
        assert row is not None
        assert row.status == StampStatus.SUCCEEDED
        assert row.response_payload is not None
        assert row.response_payload["ticket_ref"] == "INC-1001"

    def test_failure_recorded_durably(self, store: StateStore) -> None:
        ctx = _context()
        backend = FailingFakeBackend()

        result = execute_stamp(store.conn, backend, ctx)

        assert result.status == StampStatus.FAILED
        row = fetch_stamp_outbox(store.conn, result.stamp_id)
        assert row is not None
        assert row.status == StampStatus.FAILED
        assert row.response_payload is not None
        assert row.response_payload["error"] == "ticket_system_rejected"


class TestTimeoutUnknown:
    def test_timeout_records_unknown_not_failed(self, store: StateStore) -> None:
        ctx = _context()
        backend = TimeoutFakeBackend()

        result = execute_stamp(store.conn, backend, ctx)

        assert result.status == StampStatus.UNKNOWN
        row = fetch_stamp_outbox(store.conn, result.stamp_id)
        assert row is not None
        assert row.status == StampStatus.UNKNOWN
        assert row.status != StampStatus.FAILED
        assert row.response_payload is None

    def test_connection_error_records_unknown_after_pending_written(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )
        backend = MagicMock()
        backend.stamp.side_effect = ConnectionError("ticket API unreachable")

        result = execute_stamp(store.conn, backend, ctx)

        assert result.status == StampStatus.UNKNOWN
        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.status == StampStatus.UNKNOWN
        backend.stamp.assert_called_once()

    def test_programmer_error_not_swallowed_leaves_pending(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )

        with pytest.raises(ValueError, match="invalid payload shape"):
            execute_stamp(store.conn, ProgrammerErrorBackend(), ctx)

        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.status == StampStatus.PENDING


class TestRecoveryRetry:
    def test_unknown_recovery_resends_same_stamp_id(self, store: StateStore) -> None:
        ctx = _context()
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )

        execute_stamp(store.conn, TimeoutFakeBackend(), ctx)
        unknown_row = fetch_stamp_outbox(store.conn, stamp_id)
        assert unknown_row is not None
        assert unknown_row.status == StampStatus.UNKNOWN

        backend = IdempotentFakeBackend()
        recovered = execute_stamp(store.conn, backend, ctx)

        assert recovered.stamp_id == stamp_id
        assert recovered.status == StampStatus.SUCCEEDED
        assert len(backend.calls) == 1
        assert backend.calls[0][0] == stamp_id

    def test_unknown_recovery_idempotent_on_same_backend_instance(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )
        inner = IdempotentFakeBackend()
        flaky = StampThenLoseResponseBackend(inner=inner)

        first = execute_stamp(store.conn, flaky, ctx)
        assert first.status == StampStatus.UNKNOWN
        assert len(inner.calls) == 1

        recovered = execute_stamp(store.conn, inner, ctx)
        assert recovered.status == StampStatus.SUCCEEDED
        assert len(inner.calls) == 2
        assert inner.calls[0][0] == stamp_id
        assert inner.calls[1][0] == stamp_id
        assert recovered.response_payload is not None
        assert recovered.response_payload.get("idempotent_replay") is True

    def test_pending_recovery_after_restart_uses_same_stamp_id(
        self, tmp_path: Path
    ) -> None:
        db = tmp_path / "restart.db"
        ctx = _context(payload={"payload_version": "A"})
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )

        first = open_state_store(db)
        write_pending_stamp(
            first.conn,
            stamp_id=stamp_id,
            alert_identity=ctx.alert_identity,
            evidence_bundle_hash=ctx.evidence_bundle_hash,
            org_config_snapshot_hash=ctx.org_config_snapshot_hash,
            processing_attempt_identity=ctx.processing_attempt_identity,
            ticket_payload=ctx.ticket_payload,
        )
        assert _count_outbox_rows(first.conn) == 1
        first.close()

        second = open_state_store(db)
        backend = IdempotentFakeBackend()
        retry_ctx = _context(payload={"payload_version": "B"})
        result = execute_stamp(second.conn, backend, retry_ctx)

        assert result.stamp_id == stamp_id
        assert result.status == StampStatus.SUCCEEDED
        assert _count_outbox_rows(second.conn) == 1
        assert backend.calls[0][1] == {"payload_version": "A"}
        second.close()

    def test_stamp_id_stable_across_distinct_attempts(self, store: StateStore) -> None:
        ctx_a = _context(attempt="1")
        ctx_b = _context(attempt="2")
        stamp_a = derive_stamp_id(
            ctx_a.alert_identity,
            ctx_a.evidence_bundle_hash,
            ctx_a.org_config_snapshot_hash,
        )
        stamp_b = derive_stamp_id(
            ctx_b.alert_identity,
            ctx_b.evidence_bundle_hash,
            ctx_b.org_config_snapshot_hash,
        )
        assert stamp_a == stamp_b

        execute_stamp(store.conn, IdempotentFakeBackend(), ctx_a)
        row = fetch_stamp_outbox(store.conn, stamp_a)
        assert row is not None
        assert row.processing_attempt_identity == "1"

        recovered = execute_stamp(store.conn, IdempotentFakeBackend(), ctx_b)
        assert recovered.stamp_id == stamp_a
        assert recovered.status == StampStatus.SUCCEEDED

    def test_processing_attempt_identity_preserved_on_cross_attempt_recovery(
        self, store: StateStore
    ) -> None:
        """Outbox row keeps the original writer attempt; stamp_id excludes attempt."""
        ctx_a = _context(attempt="writer-1")
        ctx_b = _context(attempt="writer-2")
        stamp_id = derive_stamp_id(
            ctx_a.alert_identity,
            ctx_a.evidence_bundle_hash,
            ctx_a.org_config_snapshot_hash,
        )

        execute_stamp(store.conn, TimeoutFakeBackend(), ctx_a)
        execute_stamp(store.conn, IdempotentFakeBackend(), ctx_b)

        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.processing_attempt_identity == "writer-1"


class TestIdempotentBackend:
    def test_duplicate_stamp_id_is_idempotent_in_fake_backend(self) -> None:
        backend = IdempotentFakeBackend()
        stamp_id = derive_stamp_id("ALERT-007", "bundle-hash", "org-hash")
        payload = {"summary": "test stamp"}

        first = backend.stamp(stamp_id, payload)
        second = backend.stamp(stamp_id, payload)

        assert first.outcome == StampBackendOutcome.SUCCEEDED
        assert second.outcome == StampBackendOutcome.SUCCEEDED
        assert len(backend._stamped) == 1
        assert backend.calls[0][0] == backend.calls[1][0]
        assert second.payload is not None
        assert second.payload.get("idempotent_replay") is True

    def test_execute_stamp_returns_cached_success_without_backend_recall(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        backend = IdempotentFakeBackend()

        first = execute_stamp(store.conn, backend, ctx)
        second = execute_stamp(store.conn, backend, ctx)

        assert first.stamp_id == second.stamp_id
        assert second.status == StampStatus.SUCCEEDED
        assert len(backend.calls) == 1

    def test_execute_stamp_returns_cached_failed_without_backend_recall(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        failing = FailingFakeBackend()

        first = execute_stamp(store.conn, failing, ctx)
        assert first.status == StampStatus.FAILED

        second = execute_stamp(store.conn, MustNotBeCalledBackend(), ctx)
        assert second.status == StampStatus.FAILED
        assert second.stamp_id == first.stamp_id


class TestNonIdempotentBackendRisk:
    def test_non_idempotent_backend_risk_is_documented(self) -> None:
        assert "double-stamp" in NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK.lower()
        assert "idempotent" in NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK.lower()


class TestOutboxPersistence:
    def test_pending_payload_round_trips(self, store: StateStore) -> None:
        ctx = _context(payload={"ticket": {"title": "Suspicious login"}})
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )
        write_pending_stamp(
            store.conn,
            stamp_id=stamp_id,
            alert_identity=ctx.alert_identity,
            evidence_bundle_hash=ctx.evidence_bundle_hash,
            org_config_snapshot_hash=ctx.org_config_snapshot_hash,
            processing_attempt_identity=ctx.processing_attempt_identity,
            ticket_payload=ctx.ticket_payload,
        )
        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.status == StampStatus.PENDING
        assert row.ticket_payload == ctx.ticket_payload

    def test_response_payload_stored_as_json(self, store: StateStore) -> None:
        ctx = _context()
        execute_stamp(store.conn, IdempotentFakeBackend(), ctx)
        row = fetch_stamp_outbox(
            store.conn,
            derive_stamp_id(
                ctx.alert_identity,
                ctx.evidence_bundle_hash,
                ctx.org_config_snapshot_hash,
            ),
        )
        assert row is not None
        raw = store.conn.execute(
            "SELECT response_payload_json FROM ticket_stamp_outbox WHERE stamp_id = ?",
            (row.stamp_id,),
        ).fetchone()
        assert raw is not None
        parsed = json.loads(str(raw[0]))
        assert parsed["ticket_ref"] == "INC-1001"


class TestEmptyBundleStampPath:
    def test_empty_bundle_stamp_id_stable_on_unknown_recovery(
        self, store: StateStore
    ) -> None:
        ctx = _context(bundle=EMPTY_BUNDLE, alert="ALERT-CORR-FAIL")
        stamp_id = derive_stamp_id(
            ctx.alert_identity, EMPTY_BUNDLE, ctx.org_config_snapshot_hash
        )

        execute_stamp(store.conn, TimeoutFakeBackend(), ctx)
        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.evidence_bundle_hash == EMPTY_BUNDLE
        assert row.status == StampStatus.UNKNOWN

        recovered = execute_stamp(store.conn, IdempotentFakeBackend(), ctx)
        assert recovered.stamp_id == stamp_id
        assert recovered.status == StampStatus.SUCCEEDED
        assert _count_outbox_rows(store.conn) == 1


class TestPayloadAuthorityOnRetry:
    def test_retry_uses_durable_outbox_payload_not_fresh_context(
        self, store: StateStore
    ) -> None:
        ctx_a = _context(payload={"sent": "payload-A"})
        stamp_id = derive_stamp_id(
            ctx_a.alert_identity,
            ctx_a.evidence_bundle_hash,
            ctx_a.org_config_snapshot_hash,
        )

        execute_stamp(store.conn, TimeoutFakeBackend(), ctx_a)
        backend = IdempotentFakeBackend()
        ctx_b = _context(payload={"sent": "payload-B"})
        execute_stamp(store.conn, backend, ctx_b)

        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.ticket_payload == {"sent": "payload-A"}
        assert backend.calls[0][1] == {"sent": "payload-A"}


class TestAdditiveSchemaUpgrade:
    def test_task6_db_gains_stamp_table_without_schema_bump(
        self, task6_only_db: Path
    ) -> None:
        probe = create_guarded_connection(task6_only_db)
        before = probe.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'ticket_stamp_outbox'
            """
        ).fetchone()
        assert before is None
        version_before = probe.execute(
            "SELECT value FROM schema_meta WHERE key = ?",
            (SCHEMA_VERSION_KEY,),
        ).fetchone()
        assert version_before is not None
        assert int(version_before[0]) == SCHEMA_VERSION
        probe.close()

        store = open_state_store(task6_only_db)
        after = store.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'ticket_stamp_outbox'
            """
        ).fetchone()
        assert after is not None
        version_after = store.conn.execute(
            "SELECT value FROM schema_meta WHERE key = ?",
            (SCHEMA_VERSION_KEY,),
        ).fetchone()
        assert version_after is not None
        assert int(version_after[0]) == SCHEMA_VERSION
        store.close()


class TestRecordStampOutcomeGuard:
    def test_record_pending_outcome_rejected_and_row_unchanged(
        self, store: StateStore
    ) -> None:
        ctx = _context()
        stamp_id = derive_stamp_id(
            ctx.alert_identity,
            ctx.evidence_bundle_hash,
            ctx.org_config_snapshot_hash,
        )
        write_pending_stamp(
            store.conn,
            stamp_id=stamp_id,
            alert_identity=ctx.alert_identity,
            evidence_bundle_hash=ctx.evidence_bundle_hash,
            org_config_snapshot_hash=ctx.org_config_snapshot_hash,
            processing_attempt_identity=ctx.processing_attempt_identity,
            ticket_payload=ctx.ticket_payload,
        )

        with pytest.raises(ValueError, match="terminal or unknown status"):
            record_stamp_outcome(store.conn, stamp_id, StampStatus.PENDING, None)

        row = fetch_stamp_outbox(store.conn, stamp_id)
        assert row is not None
        assert row.status == StampStatus.PENDING
        assert row.response_payload is None
