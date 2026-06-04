"""Startup ledger chain integrity verification."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from praetor.alerts.outbox import write_pending_health_alert
from praetor.contracts.health import SystemHealthAlert
from praetor.ledger.hash_chain import LedgerChainIntegrityError, verify_ledger_chain

LEDGER_CHAIN_INTEGRITY_ALERT_CODE = "ledger_chain_integrity_failure"
DEFAULT_EXIT_CODE = 3


class LedgerStartupError(Exception):
    """Raised when startup must refuse intake due to ledger integrity failure."""

    def __init__(self, message: str, *, exit_code: int = DEFAULT_EXIT_CODE) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _refuse_ledger_startup(
    conn: sqlite3.Connection,
    exc: LedgerChainIntegrityError,
    *,
    emit_health_alert: bool,
    commit_alert: bool,
) -> None:
    if emit_health_alert:
        alert = SystemHealthAlert(
            alert_code=LEDGER_CHAIN_INTEGRITY_ALERT_CODE,
            emitted_at=datetime.now(UTC),
        )
        write_pending_health_alert(conn, alert)
        if commit_alert:
            conn.commit()
    msg = "ledger hash-chain integrity verification failed"
    raise LedgerStartupError(msg) from exc


def verify_ledger_chain_at_startup(
    conn: sqlite3.Connection,
    *,
    emit_health_alert: bool = True,
) -> None:
    """Verify chain continuity; optionally queue health alert and refuse."""
    try:
        verify_ledger_chain(conn)
    except LedgerChainIntegrityError as exc:
        _refuse_ledger_startup(
            conn,
            exc,
            emit_health_alert=emit_health_alert,
            commit_alert=False,
        )


def run_ledger_startup_hook(conn: sqlite3.Connection) -> None:
    """Task-10 startup hook: verify chain after DB open; persist alert and refuse."""
    try:
        verify_ledger_chain(conn)
    except LedgerChainIntegrityError as exc:
        _refuse_ledger_startup(
            conn,
            exc,
            emit_health_alert=True,
            commit_alert=True,
        )
