"""SQLite state layer — startup guard (Task 5); store schema in Task 6."""

from praetor.state.sqlite_guard import (
    GUARDED_ISOLATION_LEVEL,
    REQUIRED_JOURNAL_MODE,
    REQUIRED_SYNCHRONOUS_MIN,
    StartupGuardError,
    create_guarded_connection,
    critical_transaction,
    init_state_dir,
    run_startup_sqlite_guard,
    verify_connection_isolation,
    verify_critical_transaction_support,
    verify_journal_mode,
    verify_synchronous,
)

__all__ = [
    "GUARDED_ISOLATION_LEVEL",
    "REQUIRED_JOURNAL_MODE",
    "REQUIRED_SYNCHRONOUS_MIN",
    "StartupGuardError",
    "create_guarded_connection",
    "critical_transaction",
    "init_state_dir",
    "run_startup_sqlite_guard",
    "verify_connection_isolation",
    "verify_critical_transaction_support",
    "verify_journal_mode",
    "verify_synchronous",
]
