"""SQLite startup guard — WAL, explicit isolation, BEGIN IMMEDIATE critical paths."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from praetor.runtime.singleton import SingletonLock

REQUIRED_JOURNAL_MODE = "wal"
REQUIRED_SYNCHRONOUS_MIN = 1  # NORMAL
GUARDED_ISOLATION_LEVEL: None = None
DEFAULT_EXIT_CODE = 2

# TODO(Task 35): extend with full PRAGMA list from docs/operator_runbook.md

_in_critical: dict[int, bool] = {}


class StartupGuardError(Exception):
    """Raised when SQLite startup guard checks fail."""

    def __init__(self, message: str, *, exit_code: int = DEFAULT_EXIT_CODE) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def init_state_dir(db_path: Path) -> None:
    """One-shot bootstrap: persist WAL and synchronous=NORMAL on a fresh or existing DB.

    Idempotent. Does not acquire the singleton lock or run startup guard checks.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    finally:
        conn.close()


def verify_journal_mode(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA journal_mode").fetchone()
    mode = "" if row is None else str(row[0]).lower()
    if mode != REQUIRED_JOURNAL_MODE:
        msg = f"required journal_mode={REQUIRED_JOURNAL_MODE!r}, got {mode!r}"
        raise StartupGuardError(msg)


def verify_synchronous(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA synchronous").fetchone()
    level = 0 if row is None else int(row[0])
    if level < REQUIRED_SYNCHRONOUS_MIN:
        msg = (
            f"required synchronous>={REQUIRED_SYNCHRONOUS_MIN} (NORMAL), got {level}"
        )
        raise StartupGuardError(msg)


def verify_connection_isolation(conn: sqlite3.Connection) -> None:
    if conn.isolation_level is not GUARDED_ISOLATION_LEVEL:
        msg = (
            "connection isolation must be explicit "
            f"(isolation_level={GUARDED_ISOLATION_LEVEL!r}), "
            f"got {conn.isolation_level!r}"
        )
        raise StartupGuardError(msg)


def require_critical_transaction(conn: sqlite3.Connection) -> None:
    """Require caller to hold an open critical_transaction on this connection."""
    if not _in_critical.get(id(conn), False):
        msg = "operation requires an active critical_transaction"
        raise StartupGuardError(msg)


def verify_critical_transaction_support(conn: sqlite3.Connection) -> None:
    """Probe that BEGIN IMMEDIATE is usable on this connection."""
    verify_connection_isolation(conn)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
    except sqlite3.Error as err:
        msg = "BEGIN IMMEDIATE is not available on this connection"
        raise StartupGuardError(msg) from err


def create_guarded_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.isolation_level = GUARDED_ISOLATION_LEVEL
    verify_journal_mode(conn)
    verify_synchronous(conn)
    verify_connection_isolation(conn)
    return conn


@contextmanager
def critical_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Critical-path transaction using BEGIN IMMEDIATE."""
    verify_connection_isolation(conn)
    if _in_critical.get(id(conn), False):
        msg = "nested critical_transaction forbidden"
        raise StartupGuardError(msg)

    _in_critical[id(conn)] = True
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        _in_critical.pop(id(conn), None)


def run_startup_sqlite_guard(
    db_path: Path,
    *,
    singleton: SingletonLock,
) -> sqlite3.Connection:
    """Run Task 5 SQLite startup checks after singleton acquisition."""
    if not singleton.is_held:
        msg = "singleton lock must be held before SQLite startup guard"
        raise StartupGuardError(msg)

    conn = create_guarded_connection(db_path)
    verify_critical_transaction_support(conn)
    return conn
