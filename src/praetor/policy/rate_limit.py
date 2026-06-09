"""Transactional containment rate limits with sliding windows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.org_config_sections import AssetEntry
from praetor.policy.containment_policy import ContainmentTarget
from praetor.policy.state import (
    BreakerDomain,
    increment_rate_counter_in_transaction,
    is_breaker_open,
    set_rate_counter,
)
from praetor.state.sqlite_guard import require_critical_transaction

# Org config lists scopes but not numeric ceilings; Task 17 used limit=1 per scope.
DEFAULT_SCOPE_EVENT_LIMIT = 1


@dataclass(frozen=True)
class RateLimitScope:
    scope_name: str
    scope_key: str


def rate_limit_scope_key(scope: str, *, target_type: str, target_id: str) -> str:
    return f"{scope}:{target_type}:{target_id}"


def _registry_entry_for_host(
    snapshot: OrgConfigSnapshot,
    host_id: str,
) -> AssetEntry | None:
    for entry in snapshot.assets_and_asset_groups.entries:
        if isinstance(entry, AssetEntry) and entry.asset_id == host_id:
            return entry
    return None


def _asset_groups_for_registered_host(
    snapshot: OrgConfigSnapshot,
    host_id: str,
) -> list[str]:
    groups: list[str] = []
    for entry in snapshot.assets_and_asset_groups.entries:
        if not isinstance(entry, AssetEntry):
            continue
        if entry.asset_id == host_id:
            groups.append(entry.asset_id)
    return groups


def applicable_rate_limit_scopes(
    snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
) -> list[RateLimitScope]:
    """Resolve configured scopes for a containment target."""
    configured = set(snapshot.rate_limit_policy.scopes)
    scopes: list[RateLimitScope] = []

    if "per_host" in configured:
        scopes.append(
            RateLimitScope(
                scope_name="per_host",
                scope_key=rate_limit_scope_key(
                    "per_host",
                    target_type=target.target_type,
                    target_id=target.target_id,
                ),
            )
        )

    if target.target_type != "host":
        return scopes

    registry_entry = _registry_entry_for_host(snapshot, target.target_id)
    if registry_entry is None:
        return scopes

    if "per_subnet" in configured:
        scopes.append(
            RateLimitScope(
                scope_name="per_subnet",
                scope_key=rate_limit_scope_key(
                    "per_subnet",
                    target_type="subnet",
                    target_id=registry_entry.subnet_membership,
                ),
            )
        )

    if "per_asset_group" in configured:
        for asset_id in _asset_groups_for_registered_host(snapshot, target.target_id):
            scopes.append(
                RateLimitScope(
                    scope_name="per_asset_group",
                    scope_key=rate_limit_scope_key(
                        "per_asset_group",
                        target_type="asset_group",
                        target_id=asset_id,
                    ),
                )
            )

    return scopes


def _parse_window_started_at(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _window_seconds(snapshot: OrgConfigSnapshot) -> int:
    return int(snapshot.containment_circuit_breaker_policy.window_seconds)


def _effective_event_count(
    conn: sqlite3.Connection,
    *,
    scope_key: str,
    window_seconds: int,
    now: datetime,
) -> int:
    row = conn.execute(
        """
        SELECT event_count, window_started_at
        FROM containment_rate_counters
        WHERE scope_key = ?
        """,
        (scope_key,),
    ).fetchone()
    if row is None:
        return 0
    started = _parse_window_started_at(str(row[1]))
    if (now - started).total_seconds() >= float(window_seconds):
        return 0
    return int(row[0])


def is_rate_limit_exceeded_for_target(
    conn: sqlite3.Connection,
    *,
    snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
    now: datetime | None = None,
    limit: int = DEFAULT_SCOPE_EVENT_LIMIT,
) -> tuple[bool, str | None]:
    """Return whether any applicable scope is at or above its limit."""
    moment = now or datetime.now(UTC)
    window_seconds = _window_seconds(snapshot)
    for scope in applicable_rate_limit_scopes(snapshot, target):
        count = _effective_event_count(
            conn,
            scope_key=scope.scope_key,
            window_seconds=window_seconds,
            now=moment,
        )
        if count >= limit:
            return True, scope.scope_key
    return False, None


def increment_rate_limits_for_target_in_transaction(
    conn: sqlite3.Connection,
    *,
    snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
    now: datetime | None = None,
) -> None:
    """Increment all applicable scope counters inside a critical transaction."""
    require_critical_transaction(conn)
    if is_breaker_open(conn, BreakerDomain.CONTAINMENT):
        return  # counters frozen while tripped; window recovery clears is_open at gate

    moment = now or datetime.now(UTC)
    window_seconds = _window_seconds(snapshot)
    for scope in applicable_rate_limit_scopes(snapshot, target):
        _increment_scope_counter_in_transaction(
            conn,
            scope_key=scope.scope_key,
            window_seconds=window_seconds,
            now=moment,
        )


def _increment_scope_counter_in_transaction(
    conn: sqlite3.Connection,
    *,
    scope_key: str,
    window_seconds: int,
    now: datetime,
) -> int:
    current = _effective_event_count(
        conn,
        scope_key=scope_key,
        window_seconds=window_seconds,
        now=now,
    )
    if current == 0:
        set_rate_counter(conn, scope_key, 1)
        conn.execute(
            """
            UPDATE containment_rate_counters
            SET window_started_at = ?
            WHERE scope_key = ?
            """,
            (now.isoformat(), scope_key),
        )
        return 1
    return increment_rate_counter_in_transaction(conn, scope_key)


def read_scope_event_count(
    conn: sqlite3.Connection,
    *,
    scope_key: str,
    snapshot: OrgConfigSnapshot,
    now: datetime | None = None,
) -> int:
    moment = now or datetime.now(UTC)
    return _effective_event_count(
        conn,
        scope_key=scope_key,
        window_seconds=_window_seconds(snapshot),
        now=moment,
    )
