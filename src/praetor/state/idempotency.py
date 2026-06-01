"""Containment idempotency keys (docs/contracts.md §4)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class ActiveIdempotencyKey:
    idempotency_key: str
    alert_identity: str
    target_type: str
    target_id: str
    scope: str
    created_at: datetime


def insert_active_idempotency_key(
    conn: sqlite3.Connection,
    *,
    idempotency_key: str,
    alert_identity: str,
    target_type: str,
    target_id: str,
    scope: str,
) -> ActiveIdempotencyKey:
    created_at = datetime.now(UTC)
    try:
        conn.execute(
            """
            INSERT INTO idempotency_keys (
                idempotency_key, alert_identity, target_type, target_id, scope,
                created_at, cleared_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                idempotency_key,
                alert_identity,
                target_type,
                target_id,
                scope,
                created_at.isoformat(),
            ),
        )
    except sqlite3.IntegrityError as err:
        msg = f"idempotency key already registered: {idempotency_key!r}"
        raise IdempotencyKeyConflictError(msg) from err
    return ActiveIdempotencyKey(
        idempotency_key=idempotency_key,
        alert_identity=alert_identity,
        target_type=target_type,
        target_id=target_id,
        scope=scope,
        created_at=created_at,
    )


def fetch_active_idempotency_key(
    conn: sqlite3.Connection, idempotency_key: str
) -> ActiveIdempotencyKey | None:
    row = conn.execute(
        """
        SELECT idempotency_key, alert_identity, target_type, target_id, scope, created_at
        FROM idempotency_keys
        WHERE idempotency_key = ? AND cleared_at IS NULL
        """,
        (idempotency_key,),
    ).fetchone()
    if row is None:
        return None
    created_at = datetime.fromisoformat(str(row["created_at"]))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return ActiveIdempotencyKey(
        idempotency_key=str(row["idempotency_key"]),
        alert_identity=str(row["alert_identity"]),
        target_type=str(row["target_type"]),
        target_id=str(row["target_id"]),
        scope=str(row["scope"]),
        created_at=created_at,
    )


def clear_idempotency_key(conn: sqlite3.Connection, idempotency_key: str) -> None:
    cleared_at = datetime.now(UTC).isoformat()
    cur = conn.execute(
        """
        UPDATE idempotency_keys
        SET cleared_at = ?
        WHERE idempotency_key = ? AND cleared_at IS NULL
        """,
        (cleared_at, idempotency_key),
    )
    if cur.rowcount == 0:
        msg = f"no active idempotency key: {idempotency_key!r}"
        raise IdempotencyKeyNotFoundError(msg)


class IdempotencyKeyConflictError(Exception):
    """Raised when registering a duplicate active idempotency key."""


class IdempotencyKeyNotFoundError(Exception):
    """Raised when clearing or referencing a missing active idempotency key."""
