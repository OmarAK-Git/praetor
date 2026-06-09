"""Production runtime entrypoints."""

from __future__ import annotations

from pathlib import Path

from praetor.runtime.singleton import SingletonLock
from praetor.state.sqlite_guard import StartupGuardError
from praetor.state.store import StateStore, open_state_store


def open_production_state_store(
    db_path: Path,
    *,
    singleton: SingletonLock,
) -> StateStore:
    """Open the state store for production; requires a held singleton lock."""
    if not singleton.is_held:
        msg = "production startup requires a held singleton lock"
        raise StartupGuardError(msg)
    return open_state_store(db_path, singleton=singleton)
