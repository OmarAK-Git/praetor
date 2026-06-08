"""Task 6 — SQLite state store and attempt lifecycle."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason
from praetor.hashing import derive_idempotency_key
from praetor.state.attempts import (
    ActiveAttemptExistsError,
    AttemptState,
    InvalidTransitionError,
    abort_attempt,
    allocate_attempt,
    complete_attempt,
    transition_attempt,
)
from praetor.state.completed_decisions import (
    CompletedDecision,
    CompletedEdictConflictError,
    fetch_completed_decision,
    insert_completed_decision,
)
from praetor.state.idempotency import (
    IdempotencyKeyConflictError,
    IdempotencyKeyNotFoundError,
    fetch_active_idempotency_key,
)
from praetor.state.store import (
    IncompatibleSchemaError,
    StateStore,
    fetch_feed_outbox_row,
    fetch_revocation_record_json,
    open_state_store,
    read_feed_sequence_next,
)


def _advance_to_ready(conn: sqlite3.Connection, attempt_id: str) -> None:
    for state in (
        AttemptState.ACTIVE,
        AttemptState.PENDING_STAMP,
        AttemptState.STAMP_RESOLVED,
        AttemptState.READY_TO_APPEND,
    ):
        transition_attempt(conn, attempt_id, state)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    s = open_state_store(db)
    yield s
    s.close()


def _revocation_record(
    *,
    reason: RevocationReason,
    cleared: bool,
    revocation_id: str = "rev-1",
    superseded_by_directive_id: str | None = None,
) -> DirectiveRevocationRecord:
    now = datetime.now(UTC)
    return DirectiveRevocationRecord(
        revocation_id=revocation_id,
        directive_id="dir-1",
        reason=reason,
        reason_code="test_reason",
        triggered_by="tester",
        revoked_at=now,
        ledger_commit_at=now,
        idempotency_key_cleared=cleared,
        superseded_by_directive_id=superseded_by_directive_id,
    )


class TestAttemptAllocation:
    def test_at_most_one_non_terminal_per_alert(self, store: StateStore) -> None:
        first = store.allocate_attempt(
            alert_identity="ALERT-1",
            evidence_bundle_hash="bundle-a",
            org_config_snapshot_hash="snap-a",
        )
        assert first.attempt is not None
        with pytest.raises(ActiveAttemptExistsError):
            store.allocate_attempt(
                alert_identity="ALERT-1",
                evidence_bundle_hash="bundle-b",
                org_config_snapshot_hash="snap-b",
            )

    def test_completed_tuple_returns_existing_under_critical_transaction(
        self, store: StateStore
    ) -> None:
        """After completion, allocate returns existing edict inside BEGIN IMMEDIATE."""
        alloc = store.allocate_attempt(
            alert_identity="ALERT-2",
            evidence_bundle_hash="bundle-x",
            org_config_snapshot_hash="snap-x",
        )
        assert alloc.attempt is not None
        _advance_to_ready(store.conn, alloc.attempt.processing_attempt_identity)
        complete_attempt(store.conn, alloc.attempt.processing_attempt_identity)

        again = store.allocate_attempt(
            alert_identity="ALERT-2",
            evidence_bundle_hash="bundle-x",
            org_config_snapshot_hash="snap-x",
        )
        assert again.attempt is None
        assert again.completed is not None
        assert len(again.completed.decision_id) == 64

    def test_active_holder_blocks_different_tuple_then_returns_completed(
        self, store: StateStore
    ) -> None:
        """Non-terminal blocks different tuple until same tuple completes."""
        active = store.allocate_attempt(
            alert_identity="ALERT-RACE2",
            evidence_bundle_hash="bundle-a",
            org_config_snapshot_hash="snap-a",
        )
        assert active.attempt is not None
        with pytest.raises(ActiveAttemptExistsError):
            store.allocate_attempt(
                alert_identity="ALERT-RACE2",
                evidence_bundle_hash="bundle-b",
                org_config_snapshot_hash="snap-b",
            )
        _advance_to_ready(store.conn, active.attempt.processing_attempt_identity)
        complete_attempt(store.conn, active.attempt.processing_attempt_identity)
        resolved = store.allocate_attempt(
            alert_identity="ALERT-RACE2",
            evidence_bundle_hash="bundle-a",
            org_config_snapshot_hash="snap-a",
        )
        assert resolved.attempt is None
        assert resolved.completed is not None

    def test_allocate_recheck_branch_when_active_and_completed_coexist(
        self, store: StateStore
    ) -> None:
        """Defensive re-check: completed edict wins when non-terminal still listed."""
        active = store.allocate_attempt(
            alert_identity="ALERT-DEF",
            evidence_bundle_hash="bundle-active",
            org_config_snapshot_hash="snap-active",
        )
        assert active.attempt is not None
        completed = CompletedDecision(
            alert_identity="ALERT-DEF",
            evidence_bundle_hash="bundle-other",
            org_config_snapshot_hash="snap-other",
            decision_id="decision-precheck",
            processing_attempt_identity="99",
            completed_at=datetime.now(UTC),
        )
        calls = {"n": 0}
        real_fetch = fetch_completed_decision

        def fetch_side_effect(
            conn: sqlite3.Connection, **kwargs: str
        ) -> CompletedDecision | None:
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            if calls["n"] == 2:
                return completed
            return real_fetch(conn, **kwargs)

        with patch(
            "praetor.state.attempts.fetch_completed_decision",
            side_effect=fetch_side_effect,
        ):
            result = allocate_attempt(
                store.conn,
                alert_identity="ALERT-DEF",
                evidence_bundle_hash="bundle-other",
                org_config_snapshot_hash="snap-other",
            )
        assert result.attempt is None
        assert result.completed == completed
        assert calls["n"] >= 2

    def test_three_tuple_uniqueness_enforced(self, store: StateStore) -> None:
        a1 = store.allocate_attempt(
            alert_identity="ALERT-3",
            evidence_bundle_hash="b1",
            org_config_snapshot_hash="s1",
        )
        assert a1.attempt is not None
        _advance_to_ready(store.conn, a1.attempt.processing_attempt_identity)
        _, completed = complete_attempt(
            store.conn, a1.attempt.processing_attempt_identity
        )
        stored = fetch_completed_decision(
            store.conn,
            alert_identity="ALERT-3",
            evidence_bundle_hash="b1",
            org_config_snapshot_hash="s1",
        )
        assert stored == completed


class TestAttemptTransitions:
    def test_happy_path_transitions(self, store: StateStore) -> None:
        alloc = store.allocate_attempt(
            alert_identity="ALERT-4",
            evidence_bundle_hash="b",
            org_config_snapshot_hash="s",
        )
        assert alloc.attempt is not None
        aid = alloc.attempt.processing_attempt_identity
        assert alloc.attempt.state == AttemptState.ALLOCATED
        _advance_to_ready(store.conn, aid)
        finished, _ = complete_attempt(store.conn, aid)
        assert finished.state == AttemptState.COMPLETED

    _PATH_TO_STATE: dict[AttemptState, list[AttemptState]] = {
        AttemptState.ALLOCATED: [],
        AttemptState.ACTIVE: [AttemptState.ACTIVE],
        AttemptState.PENDING_STAMP: [
            AttemptState.ACTIVE,
            AttemptState.PENDING_STAMP,
        ],
        AttemptState.STAMP_RESOLVED: [
            AttemptState.ACTIVE,
            AttemptState.PENDING_STAMP,
            AttemptState.STAMP_RESOLVED,
        ],
        AttemptState.READY_TO_APPEND: [
            AttemptState.ACTIVE,
            AttemptState.PENDING_STAMP,
            AttemptState.STAMP_RESOLVED,
            AttemptState.READY_TO_APPEND,
        ],
    }

    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (AttemptState.ALLOCATED, AttemptState.COMPLETED),
            (AttemptState.ACTIVE, AttemptState.ACTIVE),
            (AttemptState.ACTIVE, AttemptState.ALLOCATED),
            (AttemptState.ACTIVE, AttemptState.COMPLETED),
            (AttemptState.PENDING_STAMP, AttemptState.ACTIVE),
            (AttemptState.READY_TO_APPEND, AttemptState.PENDING_STAMP),
        ],
    )
    def test_invalid_forward_or_skip_rejected(
        self,
        store: StateStore,
        from_state: AttemptState,
        to_state: AttemptState,
    ) -> None:
        alloc = store.allocate_attempt(
            alert_identity=f"ALERT-FSM-{from_state.value}-{to_state.value}",
            evidence_bundle_hash="b",
            org_config_snapshot_hash="s",
        )
        assert alloc.attempt is not None
        aid = alloc.attempt.processing_attempt_identity
        for state in self._PATH_TO_STATE[from_state]:
            transition_attempt(store.conn, aid, state)
        with pytest.raises(InvalidTransitionError):
            transition_attempt(store.conn, aid, to_state)

    @pytest.mark.parametrize(
        "to_state",
        [
            AttemptState.ACTIVE,
            AttemptState.ALLOCATED,
            AttemptState.ABORTED,
            AttemptState.PENDING_STAMP,
        ],
    )
    def test_completed_is_terminal_sink(
        self, store: StateStore, to_state: AttemptState
    ) -> None:
        alloc = store.allocate_attempt(
            alert_identity="ALERT-TERM-C",
            evidence_bundle_hash="b",
            org_config_snapshot_hash="s",
        )
        assert alloc.attempt is not None
        aid = alloc.attempt.processing_attempt_identity
        _advance_to_ready(store.conn, aid)
        complete_attempt(store.conn, aid)
        with pytest.raises(InvalidTransitionError):
            transition_attempt(store.conn, aid, to_state)

    @pytest.mark.parametrize(
        "to_state",
        [AttemptState.ACTIVE, AttemptState.ALLOCATED, AttemptState.COMPLETED],
    )
    def test_aborted_is_terminal_sink(
        self, store: StateStore, to_state: AttemptState
    ) -> None:
        alloc = store.allocate_attempt(
            alert_identity="ALERT-TERM-A",
            evidence_bundle_hash="b",
            org_config_snapshot_hash="s",
        )
        assert alloc.attempt is not None
        aid = alloc.attempt.processing_attempt_identity
        abort_attempt(store.conn, aid)
        with pytest.raises(InvalidTransitionError):
            transition_attempt(store.conn, aid, to_state)

    def test_aborted_allows_changed_input_retry(self, store: StateStore) -> None:
        first = store.allocate_attempt(
            alert_identity="ALERT-6",
            evidence_bundle_hash="bundle-old",
            org_config_snapshot_hash="snap-old",
        )
        assert first.attempt is not None
        abort_attempt(store.conn, first.attempt.processing_attempt_identity)
        second = store.allocate_attempt(
            alert_identity="ALERT-6",
            evidence_bundle_hash="bundle-new",
            org_config_snapshot_hash="snap-new",
        )
        assert second.attempt is not None
        assert second.completed is None

    def test_aborted_allows_same_input_retry(self, store: StateStore) -> None:
        """Aborted attempts do not block same-tuple retry."""
        first = store.allocate_attempt(
            alert_identity="ALERT-6B",
            evidence_bundle_hash="bundle-same",
            org_config_snapshot_hash="snap-same",
        )
        assert first.attempt is not None
        first_id = first.attempt.processing_attempt_identity
        abort_attempt(store.conn, first_id)
        second = store.allocate_attempt(
            alert_identity="ALERT-6B",
            evidence_bundle_hash="bundle-same",
            org_config_snapshot_hash="snap-same",
        )
        assert second.attempt is not None
        assert second.completed is None
        assert second.attempt.processing_attempt_identity != first_id


class TestCompletedEdictConflict:
    def test_duplicate_insert_raises_conflict(self, store: StateStore) -> None:
        insert_completed_decision(
            store.conn,
            alert_identity="ALERT-DUP",
            evidence_bundle_hash="b",
            org_config_snapshot_hash="s",
            decision_id="dec-1",
            processing_attempt_identity="1",
        )
        with pytest.raises(CompletedEdictConflictError):
            insert_completed_decision(
                store.conn,
                alert_identity="ALERT-DUP",
                evidence_bundle_hash="b",
                org_config_snapshot_hash="s",
                decision_id="dec-2",
                processing_attempt_identity="2",
            )
        row = fetch_completed_decision(
            store.conn,
            alert_identity="ALERT-DUP",
            evidence_bundle_hash="b",
            org_config_snapshot_hash="s",
        )
        assert row is not None
        assert row.decision_id == "dec-1"


class TestIdempotencyRegistration:
    def test_duplicate_registration_raises_conflict(self, store: StateStore) -> None:
        key = derive_idempotency_key("ALERT-I", "host", "h1", "isolate")
        store.register_idempotency_key(
            idempotency_key=key,
            alert_identity="ALERT-I",
            target_type="host",
            target_id="h1",
            scope="isolate",
        )
        with pytest.raises(IdempotencyKeyConflictError):
            store.register_idempotency_key(
                idempotency_key=key,
                alert_identity="ALERT-I",
                target_type="host",
                target_id="h1",
                scope="isolate",
            )


class TestRevocation:
    def test_manual_revocation_clears_idempotency_and_writes_outbox(
        self, store: StateStore
    ) -> None:
        key = derive_idempotency_key("ALERT-M", "host", "host-1", "isolate")
        store.register_idempotency_key(
            idempotency_key=key,
            alert_identity="ALERT-M",
            target_type="host",
            target_id="host-1",
            scope="isolate",
        )
        record = _revocation_record(reason=RevocationReason.MANUAL, cleared=True)
        result = store.write_manual_revocation(record, idempotency_key=key)
        assert result.sequence_number == 1
        assert fetch_active_idempotency_key(store.conn, key) is None
        outbox = fetch_feed_outbox_row(store.conn, 1)
        assert outbox is not None
        assert outbox["revocation_id"] == "rev-1"
        stored_json = fetch_revocation_record_json(store.conn, "rev-1")
        assert stored_json is not None
        assert "manual" in stored_json

    def test_manual_revocation_rolls_back_when_key_missing(
        self, store: StateStore
    ) -> None:
        record = _revocation_record(
            reason=RevocationReason.MANUAL,
            cleared=True,
            revocation_id="rev-missing-key",
        )
        with pytest.raises(IdempotencyKeyNotFoundError):
            store.write_manual_revocation(
                record, idempotency_key="nonexistent-key"
            )
        assert fetch_revocation_record_json(store.conn, "rev-missing-key") is None
        assert fetch_feed_outbox_row(store.conn, 1) is None
        assert read_feed_sequence_next(store.conn) == 1

    def test_automated_revocation_retains_idempotency_key(
        self, store: StateStore
    ) -> None:
        key = derive_idempotency_key("ALERT-A", "host", "host-2", "isolate")
        store.register_idempotency_key(
            idempotency_key=key,
            alert_identity="ALERT-A",
            target_type="host",
            target_id="host-2",
            scope="isolate",
        )
        record = _revocation_record(
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            cleared=False,
            revocation_id="rev-auto",
        )
        result = store.write_automated_revocation(record)
        assert result.sequence_number == 1
        assert fetch_active_idempotency_key(store.conn, key) is not None
        outbox = fetch_feed_outbox_row(store.conn, 1)
        assert outbox is not None
        assert outbox["status"] == "pending"

    def test_failed_revocation_does_not_consume_sequence(
        self, store: StateStore
    ) -> None:
        first = _revocation_record(
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            cleared=False,
            revocation_id="rev-dup",
        )
        store.write_automated_revocation(first)
        duplicate = _revocation_record(
            reason=RevocationReason.SUPERSESSION,
            cleared=False,
            revocation_id="rev-dup",
            superseded_by_directive_id="dir-2",
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.write_automated_revocation(duplicate)
        success = _revocation_record(
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            cleared=False,
            revocation_id="rev-next",
        )
        result = store.write_automated_revocation(success)
        assert result.sequence_number == 2
        assert read_feed_sequence_next(store.conn) == 3

    def test_feed_sequence_survives_store_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "reopen.db"
        store1 = open_state_store(db)
        key = derive_idempotency_key("ALERT-R", "host", "h", "s")
        store1.register_idempotency_key(
            idempotency_key=key,
            alert_identity="ALERT-R",
            target_type="host",
            target_id="h",
            scope="s",
        )
        manual = _revocation_record(
            reason=RevocationReason.MANUAL,
            cleared=True,
            revocation_id="rev-reopen-1",
        )
        r1 = store1.write_manual_revocation(manual, idempotency_key=key)
        assert r1.sequence_number == 1
        store1.close()

        store2 = open_state_store(db)
        auto = _revocation_record(
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            cleared=False,
            revocation_id="rev-reopen-2",
        )
        r2 = store2.write_automated_revocation(auto)
        assert r2.sequence_number == 2
        store2.close()

    def test_manual_and_automated_share_gap_free_sequence(
        self, store: StateStore
    ) -> None:
        key = derive_idempotency_key("ALERT-S", "host", "h", "s")
        store.register_idempotency_key(
            idempotency_key=key,
            alert_identity="ALERT-S",
            target_type="host",
            target_id="h",
            scope="s",
        )
        manual = _revocation_record(
            reason=RevocationReason.MANUAL,
            cleared=True,
            revocation_id="rev-m",
        )
        auto = _revocation_record(
            reason=RevocationReason.SUPERSESSION,
            cleared=False,
            revocation_id="rev-s",
            superseded_by_directive_id="dir-2",
        )
        r1 = store.write_manual_revocation(manual, idempotency_key=key)
        r2 = store.write_automated_revocation(auto)
        assert r1.sequence_number == 1
        assert r2.sequence_number == 2


class TestSchemaVersion:
    def test_rejects_incompatible_schema_version(self, tmp_path: Path) -> None:
        db = tmp_path / "schema.db"
        first = open_state_store(db)
        first.conn.execute(
            "UPDATE schema_meta SET value = '999' WHERE key = 'schema_version'"
        )
        first.close()
        with pytest.raises(IncompatibleSchemaError):
            open_state_store(db)


class TestOpenStateStoreContract:
    def test_open_state_store_does_not_acquire_singleton(
        self, tmp_path: Path
    ) -> None:
        """Two handles can open; production must pass a SingletonLock."""
        db = tmp_path / "multi.db"
        a = open_state_store(db)
        b = open_state_store(db)
        try:
            a.allocate_attempt(
                alert_identity="ALERT-MULTI",
                evidence_bundle_hash="b",
                org_config_snapshot_hash="s",
            )
            with pytest.raises(ActiveAttemptExistsError):
                b.allocate_attempt(
                    alert_identity="ALERT-MULTI",
                    evidence_bundle_hash="b2",
                    org_config_snapshot_hash="s2",
                )
        finally:
            a.close()
            b.close()

    def test_store_module_documents_single_writer_and_singleton_caller(
        self,
    ) -> None:
        from praetor.state import store as store_mod

        doc = store_mod.__doc__ or ""
        assert "single-writer" in doc.lower() or "single writer" in doc.lower()
        assert "singleton" in doc.lower()
