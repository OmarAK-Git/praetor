"""Task 11 — revocation feed startup recovery."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN
from tests.revocation.test_feed_exporter import FailingFeedSink, _revocation

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.revocation.exporter import (
    default_feed_jsonl_path,
    export_next_pending_row,
    is_feed_actuation_blocked,
)
from praetor.revocation.outbox import (
    is_feed_unhealthy,
    mark_feed_row_exported,
    read_last_verified_exported_sequence,
)
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import open_state_store


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "state.db"


def test_startup_recovers_pending_feed_rows(
    db_path: Path, verifier: PrincipalMapVerifier
) -> None:
    store = open_state_store(db_path)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    store.write_automated_revocation(_revocation(revocation_id="rev-startup"))
    store.close()

    reopened = open_state_store(db_path)
    try:
        feed_path = default_feed_jsonl_path(db_path)
        assert feed_path.exists()
        lines = feed_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["sequence_number"] == 1
        assert not is_feed_actuation_blocked(
            reopened.conn, propagation_delay_seconds=60
        )
    finally:
        reopened.close()


def test_startup_degraded_when_feed_over_slo(
    db_path: Path, verifier: PrincipalMapVerifier
) -> None:
    store = open_state_store(db_path)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    old = datetime.now(UTC) - timedelta(seconds=120)
    store.write_automated_revocation(
        _revocation(revocation_id="rev-stale", ledger_commit_at=old)
    )
    for _ in range(3):
        export_next_pending_row(
            store.conn, sink=FailingFeedSink(), max_feed_export_retries=3
        )
    store.close()

    reopened = open_state_store(db_path)
    try:
        assert is_feed_actuation_blocked(
            reopened.conn, propagation_delay_seconds=60
        )
    finally:
        reopened.close()


def test_startup_recovers_after_transient_unhealthy(
    db_path: Path, verifier: PrincipalMapVerifier
) -> None:
    store = open_state_store(db_path)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    store.write_automated_revocation(_revocation(revocation_id="rev-transient"))
    for _ in range(3):
        export_next_pending_row(
            store.conn, sink=FailingFeedSink(), max_feed_export_retries=3
        )
    assert is_feed_unhealthy(store.conn)
    store.close()

    reopened = open_state_store(db_path)
    try:
        feed_path = default_feed_jsonl_path(db_path)
        assert feed_path.exists()
        assert read_last_verified_exported_sequence(reopened.conn) == 1
        assert not is_feed_unhealthy(reopened.conn)
        assert not is_feed_actuation_blocked(
            reopened.conn, propagation_delay_seconds=60
        )
    finally:
        reopened.close()


def test_startup_marks_unhealthy_when_feed_file_missing_but_metadata_exported(
    db_path: Path, verifier: PrincipalMapVerifier
) -> None:
    store = open_state_store(db_path)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    store.write_automated_revocation(_revocation(revocation_id="rev-missing-file"))
    feed_path = default_feed_jsonl_path(db_path)
    with critical_transaction(store.conn):
        mark_feed_row_exported(store.conn, sequence_number=1)
    store.conn.commit()
    if feed_path.exists():
        feed_path.unlink()
    store.close()

    reopened = open_state_store(db_path)
    try:
        assert read_last_verified_exported_sequence(reopened.conn) == 1
        assert is_feed_unhealthy(reopened.conn)
        assert is_feed_actuation_blocked(
            reopened.conn, propagation_delay_seconds=60
        )
    finally:
        reopened.close()
