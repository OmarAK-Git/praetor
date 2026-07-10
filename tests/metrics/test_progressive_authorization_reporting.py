"""V2-032 progressive authorization reporting tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tests.ledger.conftest import sample_decision_edict

from praetor.annotations.store import (
    init_annotation_schema,
    submit_annotation,
)
from praetor.auth import Principal, PrincipalMapVerifier
from praetor.contracts.disposition import Disposition
from praetor.ledger.store import append_ledger_record, init_ledger_schema
from praetor.metrics.evaluations import (
    init_policy_gate_evaluation_schema,
    record_policy_gate_evaluation,
)
from praetor.reporting.progressive_authorization import (
    PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY,
    build_progressive_authorization_report,
)
from praetor.state.sqlite_guard import (
    create_guarded_connection,
    critical_transaction,
    init_state_dir,
)
from praetor.state.store import init_state_schema
from praetor.tickets.outbox import init_stamp_outbox_schema

WINDOW_START = datetime(2026, 6, 13, 0, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 6, 14, 0, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 6, 13, 10, 0, 0, tzinfo=UTC)
T2 = datetime(2026, 6, 13, 11, 0, 0, tzinfo=UTC)
T3 = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
OUTSIDE = datetime(2026, 6, 12, 23, 0, 0, tzinfo=UTC)

ANALYST = Principal(identity="analyst@example.com", role="analyst")
ANALYST_TOKEN = "token-analyst"


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier({ANALYST_TOKEN: ANALYST})


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    from praetor.alerts.outbox import init_health_alert_outbox_schema

    db_path = tmp_path / "state.db"
    init_state_dir(db_path)
    connection = create_guarded_connection(db_path)
    connection.row_factory = sqlite3.Row
    init_state_schema(connection)
    init_stamp_outbox_schema(connection)
    init_health_alert_outbox_schema(connection)
    init_ledger_schema(connection)
    init_annotation_schema(connection)
    init_policy_gate_evaluation_schema(connection)
    connection.commit()
    yield connection
    connection.close()


def _append_edict(conn: sqlite3.Connection, *, decision_id: str) -> None:
    edict = sample_decision_edict(decision_id=decision_id)
    with critical_transaction(conn):
        append_ledger_record(conn, edict)


def _record_evaluation(
    conn: sqlite3.Connection,
    *,
    decision_id: str,
    target_type: str,
    asset_class: str,
    proposed: Disposition,
    final: Disposition,
    evaluated_at: datetime,
) -> None:
    with critical_transaction(conn):
        record_policy_gate_evaluation(
            conn,
            decision_id=decision_id,
            target_type=target_type,
            asset_class=asset_class,
            proposed=proposed,
            final=final,
            evaluated_at=evaluated_at,
        )


def _submit_annotation(
    conn: sqlite3.Connection,
    verifier: PrincipalMapVerifier,
    *,
    decision_id: str,
    disposition_correct: bool,
    corrected_disposition: Disposition | None,
    comment: str,
    timestamp: datetime,
) -> None:
    with critical_transaction(conn):
        submit_annotation(
            conn,
            token=ANALYST_TOKEN,
            verifier=verifier,
            decision_id=decision_id,
            disposition_correct=disposition_correct,
            corrected_disposition=corrected_disposition,
            comment=comment,
            timestamp=timestamp,
        )


def test_empty_window_returns_no_dimensions(conn: sqlite3.Connection) -> None:
    report = build_progressive_authorization_report(
        conn,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert report.policy_gate_by_dimension == ()
    assert report.annotation_outcomes_by_dimension == ()
    assert report.read_only is PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY


def test_aggregates_policy_gate_override_rate_by_dimension(
    conn: sqlite3.Connection,
) -> None:
    _record_evaluation(
        conn,
        decision_id="dec-host-1",
        target_type="host",
        asset_class="eng-workstation-pool",
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.AUTO_CONTAIN,
        evaluated_at=T1,
    )
    _record_evaluation(
        conn,
        decision_id="dec-host-2",
        target_type="host",
        asset_class="eng-workstation-pool",
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.ESCALATE,
        evaluated_at=T2,
    )
    _record_evaluation(
        conn,
        decision_id="dec-acct-1",
        target_type="account",
        asset_class="privileged-account-pool",
        proposed=Disposition.STANDARD_REVIEW,
        final=Disposition.STANDARD_REVIEW,
        evaluated_at=T3,
    )
    conn.commit()

    report = build_progressive_authorization_report(
        conn,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert len(report.policy_gate_by_dimension) == 2
    host = next(
        row for row in report.policy_gate_by_dimension if row.target_type == "host"
    )
    account = next(
        row for row in report.policy_gate_by_dimension if row.target_type == "account"
    )
    assert host.asset_class == "eng-workstation-pool"
    assert host.policy_gate_evaluations_total == 2
    assert host.policy_gate_override_total == 1
    assert host.policy_gate_override_rate == pytest.approx(0.5)
    assert account.policy_gate_evaluations_total == 1
    assert account.policy_gate_override_total == 0
    assert account.policy_gate_override_rate == pytest.approx(0.0)


def test_excludes_evaluations_outside_window(conn: sqlite3.Connection) -> None:
    _record_evaluation(
        conn,
        decision_id="dec-outside",
        target_type="host",
        asset_class="eng-workstation-pool",
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.ESCALATE,
        evaluated_at=OUTSIDE,
    )
    conn.commit()

    report = build_progressive_authorization_report(
        conn,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert report.policy_gate_by_dimension == ()


def test_aggregates_annotation_outcomes_by_dimension(
    conn: sqlite3.Connection,
    verifier: PrincipalMapVerifier,
) -> None:
    _append_edict(conn, decision_id="dec-ann-host-1")
    _append_edict(conn, decision_id="dec-ann-host-2")
    _record_evaluation(
        conn,
        decision_id="dec-ann-host-1",
        target_type="host",
        asset_class="eng-workstation-pool",
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.AUTO_CONTAIN,
        evaluated_at=T1,
    )
    _record_evaluation(
        conn,
        decision_id="dec-ann-host-2",
        target_type="host",
        asset_class="eng-workstation-pool",
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.ESCALATE,
        evaluated_at=T2,
    )
    _submit_annotation(
        conn,
        verifier,
        decision_id="dec-ann-host-1",
        disposition_correct=True,
        corrected_disposition=None,
        comment="confirmed",
        timestamp=T1 + timedelta(minutes=5),
    )
    _submit_annotation(
        conn,
        verifier,
        decision_id="dec-ann-host-2",
        disposition_correct=False,
        corrected_disposition=Disposition.STANDARD_REVIEW,
        comment="too aggressive",
        timestamp=T2 + timedelta(minutes=5),
    )
    conn.commit()

    report = build_progressive_authorization_report(
        conn,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert len(report.annotation_outcomes_by_dimension) == 1
    outcome = report.annotation_outcomes_by_dimension[0]
    assert outcome.target_type == "host"
    assert outcome.asset_class == "eng-workstation-pool"
    assert outcome.annotations_total == 2
    assert outcome.disposition_correct_total == 1
    assert outcome.disposition_incorrect_total == 1
    assert outcome.disposition_correct_rate == pytest.approx(0.5)
    assert outcome.corrected_disposition_counts == {"standard_review": 1}


def test_report_builder_is_read_only(
    conn: sqlite3.Connection,
    verifier: PrincipalMapVerifier,
) -> None:
    _append_edict(conn, decision_id="dec-readonly")
    _record_evaluation(
        conn,
        decision_id="dec-readonly",
        target_type="host",
        asset_class="eng-workstation-pool",
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.AUTO_CONTAIN,
        evaluated_at=T1,
    )
    _submit_annotation(
        conn,
        verifier,
        decision_id="dec-readonly",
        disposition_correct=True,
        corrected_disposition=None,
        comment="ok",
        timestamp=T1 + timedelta(minutes=1),
    )
    conn.commit()

    eval_count_before = conn.execute(
        "SELECT COUNT(*) FROM policy_gate_evaluations"
    ).fetchone()[0]
    annotation_count_before = conn.execute(
        "SELECT COUNT(*) FROM analyst_annotations"
    ).fetchone()[0]
    ledger_count_before = conn.execute(
        "SELECT COUNT(*) FROM ledger_chain"
    ).fetchone()[0]

    report = build_progressive_authorization_report(
        conn,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    eval_count_after = conn.execute(
        "SELECT COUNT(*) FROM policy_gate_evaluations"
    ).fetchone()[0]
    annotation_count_after = conn.execute(
        "SELECT COUNT(*) FROM analyst_annotations"
    ).fetchone()[0]
    ledger_count_after = conn.execute(
        "SELECT COUNT(*) FROM ledger_chain"
    ).fetchone()[0]

    assert report.read_only is True
    assert eval_count_after == eval_count_before
    assert annotation_count_after == annotation_count_before
    assert ledger_count_after == ledger_count_before
