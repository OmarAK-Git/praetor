"""V2-017 production state initialization guard tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from praetor.annotations.store import init_annotation_schema
from praetor.config.state import init_config_schema
from praetor.ledger.store import init_ledger_schema
from praetor.revocation.outbox import init_revocation_feed_export_schema
from praetor.runtime.singleton import SingletonLock
from praetor.runtime.startup import open_production_state_store
from praetor.state.sqlite_guard import create_guarded_connection, init_state_dir
from praetor.state.store import (
    SCHEMA_VERSION_KEY,
    IncompatibleSchemaError,
    init_state_schema,
)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


REQUIRED_PRODUCTION_TABLES = frozenset(
    {
        "analyst_annotations",
        "containment_rate_counters",
        "circuit_breaker_state",
        "provider_health_metrics",
        "revocation_feed_export_meta",
    }
)


def _init_pre_policy_fixture_db(db_path: Path) -> None:
    """Older additive DB without policy tables (V2-017 upgrade path)."""
    init_state_dir(db_path)
    conn = create_guarded_connection(db_path)
    init_state_schema(conn)
    init_config_schema(conn)
    init_ledger_schema(conn)
    init_annotation_schema(conn)
    init_revocation_feed_export_schema(conn)
    conn.commit()
    conn.close()


def test_production_state_store_creates_required_policy_tables(
    tmp_path: Path,
) -> None:
    db = tmp_path / "prod-tables.db"
    init_state_dir(db)
    with SingletonLock(tmp_path) as lock:
        store = open_production_state_store(db, singleton=lock)
        try:
            tables = _table_names(store.conn)
            missing = REQUIRED_PRODUCTION_TABLES - tables
            assert not missing, f"missing production tables: {sorted(missing)}"
            breaker_cols = {
                str(row[1])
                for row in store.conn.execute(
                    "PRAGMA table_info(circuit_breaker_state)"
                )
            }
            assert "half_open" in breaker_cols
            assert "opened_at" in breaker_cols
            metrics = store.conn.execute(
                "SELECT COUNT(*) FROM provider_health_metrics WHERE id = 1"
            ).fetchone()
            assert metrics is not None and int(metrics[0]) == 1
        finally:
            store.close()


def test_production_state_additive_fixture_gets_new_tables(
    tmp_path: Path,
) -> None:
    db = tmp_path / "pre_policy.db"
    _init_pre_policy_fixture_db(db)
    conn = sqlite3.connect(db)
    try:
        before = _table_names(conn)
        assert "containment_rate_counters" not in before
        assert "circuit_breaker_state" not in before
        assert "provider_health_metrics" not in before
    finally:
        conn.close()

    init_state_dir(db)
    with SingletonLock(tmp_path) as lock:
        store = open_production_state_store(db, singleton=lock)
        try:
            after = _table_names(store.conn)
            assert REQUIRED_PRODUCTION_TABLES <= after
        finally:
            store.close()


def test_production_state_rejects_incompatible_schema_version(
    tmp_path: Path,
) -> None:
    db = tmp_path / "bad_schema.db"
    init_state_dir(db)
    conn = create_guarded_connection(db)
    init_state_schema(conn)
    conn.execute(
        "UPDATE schema_meta SET value = ? WHERE key = ?",
        ("999", SCHEMA_VERSION_KEY),
    )
    conn.commit()
    conn.close()

    with SingletonLock(tmp_path) as lock:
        with pytest.raises(IncompatibleSchemaError, match="incompatible state schema"):
            open_production_state_store(db, singleton=lock)
