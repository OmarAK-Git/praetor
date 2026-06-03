"""Internal-only config operations (not external write surfaces)."""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.config.errors import InternalOnlyConfigOperationError
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore


def _guard_internal(operation: str) -> None:
    raise InternalOnlyConfigOperationError(
        f"{operation} is internal-only and not an authenticated external surface"
    )


def purge_expired_emergency_records_internal(
    store: StateStore,
) -> int:
    """Expire emergencies by wall clock; internal maintenance only."""
    moment = datetime.now(UTC).isoformat()
    with critical_transaction(store.conn):
        cur = store.conn.execute(
            "DELETE FROM emergency_never_contain_records WHERE expires_at <= ?",
            (moment,),
        )
        return int(cur.rowcount)
