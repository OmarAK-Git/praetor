"""TASK-025 analyst annotation storage tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.ledger.conftest import sample_decision_edict

from praetor.annotations.store import (
    AnnotationStoreError,
    fetch_annotations_for_decision,
    fetch_edict_ledger_hash,
    init_annotation_schema,
    submit_annotation,
)
from praetor.auth import (
    InsufficientRoleError,
    Principal,
    PrincipalMapVerifier,
    SelfAssertedIdentityError,
)
from praetor.contracts.disposition import Disposition
from praetor.ledger.store import append_ledger_record, fetch_ledger_rows
from praetor.state.completed_decisions import insert_completed_decision
from praetor.state.sqlite_guard import (
    StartupGuardError,
    create_guarded_connection,
    critical_transaction,
)
from praetor.state.store import init_state_schema, open_state_store
from praetor.tickets.outbox import init_stamp_outbox_schema

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)

ANALYST = Principal(identity="analyst@example.com", role="analyst")
SOC_LEAD = Principal(identity="lead@example.com", role="soc_lead")
ANALYST_TOKEN = "token-analyst"
SOC_LEAD_TOKEN = "token-soc-lead"


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {
            ANALYST_TOKEN: ANALYST,
            SOC_LEAD_TOKEN: SOC_LEAD,
        }
    )


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    from praetor.alerts.outbox import init_health_alert_outbox_schema
    from praetor.ledger.store import init_ledger_schema
    from praetor.state.sqlite_guard import init_state_dir

    db_path = tmp_path / "state.db"
    init_state_dir(db_path)
    connection = create_guarded_connection(db_path)
    connection.row_factory = sqlite3.Row
    init_state_schema(connection)
    init_stamp_outbox_schema(connection)
    init_health_alert_outbox_schema(connection)
    init_ledger_schema(connection)
    init_annotation_schema(connection)
    connection.commit()
    yield connection
    connection.close()


def _append_edict(conn: sqlite3.Connection, *, decision_id: str = "dec-ann-1") -> str:
    edict = sample_decision_edict(decision_id=decision_id)
    with critical_transaction(conn):
        result = append_ledger_record(conn, edict)
    conn.commit()
    return result.ledger_current_hash


class TestCrossFieldValidation:
    def test_incorrect_disposition_requires_correction(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn)
        with critical_transaction(conn):
            with pytest.raises(AnnotationStoreError) as exc_info:
                submit_annotation(
                    conn,
                    token=ANALYST_TOKEN,
                    verifier=verifier,
                    decision_id="dec-ann-1",
                    disposition_correct=False,
                    corrected_disposition=None,
                    comment="wrong call",
                    timestamp=NOW,
                )
        assert exc_info.value.code == "invalid_annotation"

    def test_correct_disposition_forbids_correction(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn)
        with critical_transaction(conn):
            with pytest.raises(AnnotationStoreError) as exc_info:
                submit_annotation(
                    conn,
                    token=ANALYST_TOKEN,
                    verifier=verifier,
                    decision_id="dec-ann-1",
                    disposition_correct=True,
                    corrected_disposition=Disposition.ESCALATE,
                    comment="contradictory",
                    timestamp=NOW,
                )
        assert exc_info.value.code == "invalid_annotation"


class TestReviewerIdentity:
    def test_stored_reviewer_identity_is_verified_principal(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn)
        with critical_transaction(conn):
            stored = submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id="dec-ann-1",
                disposition_correct=True,
                corrected_disposition=None,
                comment="agree",
                timestamp=NOW,
            )
        conn.commit()

        assert stored.annotation.reviewer_identity == "analyst@example.com"
        assert stored.annotation.reviewer_identity != ANALYST_TOKEN

    def test_self_asserted_reviewer_identity_rejected(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn)
        with critical_transaction(conn):
            with pytest.raises(SelfAssertedIdentityError):
                submit_annotation(
                    conn,
                    token=ANALYST_TOKEN,
                    verifier=verifier,
                    decision_id="dec-ann-1",
                    disposition_correct=True,
                    corrected_disposition=None,
                    comment="spoof",
                    timestamp=NOW,
                    caller_supplied_reviewer_identity="soc-lead@evil.com",
                )

    def test_wrong_role_rejected(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn)
        with critical_transaction(conn):
            with pytest.raises(InsufficientRoleError):
                submit_annotation(
                    conn,
                    token=SOC_LEAD_TOKEN,
                    verifier=verifier,
                    decision_id="dec-ann-1",
                    disposition_correct=True,
                    corrected_disposition=None,
                    comment="not analyst",
                    timestamp=NOW,
                )


class TestDecisionLinkage:
    def test_unknown_decision_id_rejected(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        with critical_transaction(conn):
            with pytest.raises(AnnotationStoreError) as exc_info:
                submit_annotation(
                    conn,
                    token=ANALYST_TOKEN,
                    verifier=verifier,
                    decision_id="dec-missing",
                    disposition_correct=True,
                    corrected_disposition=None,
                    comment="orphan",
                    timestamp=NOW,
                )
        assert exc_info.value.code == "unknown_decision_id"

    def test_annotation_links_to_existing_decision(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn, decision_id="dec-linked")
        with critical_transaction(conn):
            stored = submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id="dec-linked",
                disposition_correct=False,
                corrected_disposition=Disposition.ESCALATE,
                comment="should have escalated",
                timestamp=NOW,
            )
        conn.commit()

        fetched = fetch_annotations_for_decision(conn, "dec-linked")
        assert len(fetched) == 1
        assert fetched[0].annotation_id == stored.annotation_id
        assert fetched[0].decision_id == "dec-linked"
        assert fetched[0].annotation.comment == "should have escalated"
        assert fetched[0].annotation.corrected_disposition == Disposition.ESCALATE

    def test_annotation_links_via_completed_decisions_only(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        decision_id = "dec-completed-only"
        with critical_transaction(conn):
            insert_completed_decision(
                conn,
                alert_identity="ALERT-COMP",
                evidence_bundle_hash="sha256:bundle:comp",
                org_config_snapshot_hash="sha256:org:comp",
                decision_id=decision_id,
                processing_attempt_identity="attempt-comp-1",
            )
            stored = submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id=decision_id,
                disposition_correct=True,
                corrected_disposition=None,
                comment="completed row only",
                timestamp=NOW,
            )
        conn.commit()

        fetched = fetch_annotations_for_decision(conn, decision_id)
        assert len(fetched) == 1
        assert fetched[0].annotation_id == stored.annotation_id
        assert fetched[0].decision_id == decision_id


class TestAnnotationOrdering:
    def test_fetch_returns_annotations_oldest_first(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn, decision_id="dec-multi")
        with critical_transaction(conn):
            first = submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id="dec-multi",
                disposition_correct=True,
                corrected_disposition=None,
                comment="first",
                timestamp=NOW,
            )
            second = submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id="dec-multi",
                disposition_correct=False,
                corrected_disposition=Disposition.ESCALATE,
                comment="second",
                timestamp=NOW,
            )
        conn.commit()

        fetched = fetch_annotations_for_decision(conn, "dec-multi")
        assert len(fetched) == 2
        assert fetched[0].annotation_id == first.annotation_id
        assert fetched[1].annotation_id == second.annotation_id
        assert fetched[0].annotation_id < fetched[1].annotation_id
        assert fetched[0].annotation.comment == "first"
        assert fetched[1].annotation.comment == "second"


class TestCriticalTransactionGuard:
    def test_submit_requires_critical_transaction(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(conn)
        with pytest.raises(StartupGuardError, match="critical_transaction"):
            submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id="dec-ann-1",
                disposition_correct=True,
                corrected_disposition=None,
                comment="no tx",
                timestamp=NOW,
            )


class TestProductionStartup:
    def test_open_state_store_inits_annotation_schema(self, tmp_path: Path) -> None:
        store = open_state_store(tmp_path / "state.db")
        try:
            row = store.conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'analyst_annotations'
                """
            ).fetchone()
            assert row is not None
        finally:
            store.close()


class TestEdictImmutability:
    def test_annotation_does_not_alter_prior_edict_hash(
        self, conn: sqlite3.Connection, verifier: PrincipalMapVerifier
    ) -> None:
        decision_id = "dec-immutable"
        hash_before = _append_edict(conn, decision_id=decision_id)
        ledger_rows_before = fetch_ledger_rows(conn)

        with critical_transaction(conn):
            submit_annotation(
                conn,
                token=ANALYST_TOKEN,
                verifier=verifier,
                decision_id=decision_id,
                disposition_correct=True,
                corrected_disposition=None,
                comment="no change to edict",
                timestamp=NOW,
            )
        conn.commit()

        hash_after = fetch_edict_ledger_hash(conn, decision_id)
        ledger_rows_after = fetch_ledger_rows(conn)

        assert hash_before == hash_after
        assert ledger_rows_before == ledger_rows_after
