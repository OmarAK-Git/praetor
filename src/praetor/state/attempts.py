"""Processing attempt lifecycle (docs/spec.md § Durable Lifecycle)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from praetor.hashing import derive_decision_id
from praetor.state.completed_decisions import (
    CompletedDecision,
    fetch_completed_decision,
    insert_completed_decision,
)
from praetor.state.sqlite_guard import critical_transaction

TERMINAL_STATES = frozenset({"completed", "aborted"})
NON_TERMINAL_STATES = frozenset(
    {
        "allocated",
        "active",
        "pending_stamp",
        "stamp_resolved",
        "ready_to_append",
    }
)


class AttemptState(str, Enum):
    ALLOCATED = "allocated"
    ACTIVE = "active"
    PENDING_STAMP = "pending_stamp"
    STAMP_RESOLVED = "stamp_resolved"
    READY_TO_APPEND = "ready_to_append"
    COMPLETED = "completed"
    ABORTED = "aborted"


_ALLOWED_TRANSITIONS: dict[AttemptState, frozenset[AttemptState]] = {
    AttemptState.ALLOCATED: frozenset({AttemptState.ACTIVE, AttemptState.ABORTED}),
    AttemptState.ACTIVE: frozenset(
        {AttemptState.PENDING_STAMP, AttemptState.ABORTED}
    ),
    AttemptState.PENDING_STAMP: frozenset(
        {AttemptState.STAMP_RESOLVED, AttemptState.ABORTED}
    ),
    AttemptState.STAMP_RESOLVED: frozenset(
        {AttemptState.READY_TO_APPEND, AttemptState.ABORTED}
    ),
    AttemptState.READY_TO_APPEND: frozenset(
        {AttemptState.COMPLETED, AttemptState.ABORTED}
    ),
    AttemptState.COMPLETED: frozenset(),
    AttemptState.ABORTED: frozenset(),
}


@dataclass(frozen=True)
class ProcessingAttempt:
    processing_attempt_identity: str
    alert_identity: str
    evidence_bundle_hash: str
    org_config_snapshot_hash: str
    state: AttemptState
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AllocationResult:
    """Outcome of attempt allocation inside a critical transaction."""

    completed: CompletedDecision | None
    attempt: ProcessingAttempt | None


class StateStoreError(Exception):
    """Base error for state store lifecycle violations."""


class ActiveAttemptExistsError(StateStoreError):
    """Raised when a non-terminal attempt already exists for alert_identity."""


class InvalidTransitionError(StateStoreError):
    """Raised when an attempt state transition is not allowed."""


class AttemptNotFoundError(StateStoreError):
    """Raised when the referenced attempt does not exist."""


def _format_attempt_id(row_id: int) -> str:
    return str(row_id)


def _row_to_attempt(row: sqlite3.Row) -> ProcessingAttempt:
    created_at = datetime.fromisoformat(str(row["created_at"]))
    updated_at = datetime.fromisoformat(str(row["updated_at"]))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    return ProcessingAttempt(
        processing_attempt_identity=_format_attempt_id(int(row["attempt_id"])),
        alert_identity=str(row["alert_identity"]),
        evidence_bundle_hash=str(row["evidence_bundle_hash"]),
        org_config_snapshot_hash=str(row["org_config_snapshot_hash"]),
        state=AttemptState(str(row["state"])),
        created_at=created_at,
        updated_at=updated_at,
    )


def _fetch_attempt_by_id(
    conn: sqlite3.Connection, processing_attempt_identity: str
) -> ProcessingAttempt | None:
    row = conn.execute(
        """
        SELECT attempt_id, alert_identity, evidence_bundle_hash,
               org_config_snapshot_hash, state, created_at, updated_at
        FROM processing_attempts
        WHERE attempt_id = ?
        """,
        (int(processing_attempt_identity),),
    ).fetchone()
    if row is None:
        return None
    return _row_to_attempt(row)


def _fetch_non_terminal_for_alert(
    conn: sqlite3.Connection, alert_identity: str
) -> ProcessingAttempt | None:
    row = conn.execute(
        """
        SELECT attempt_id, alert_identity, evidence_bundle_hash,
               org_config_snapshot_hash, state, created_at, updated_at
        FROM processing_attempts
        WHERE alert_identity = ? AND state NOT IN ('completed', 'aborted')
        """,
        (alert_identity,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_attempt(row)


def allocate_attempt(
    conn: sqlite3.Connection,
    *,
    alert_identity: str,
    evidence_bundle_hash: str,
    org_config_snapshot_hash: str,
) -> AllocationResult:
    """Allocate or return existing completed edict (docs/contracts.md §6 intake-race rule)."""
    with critical_transaction(conn):
        existing = fetch_completed_decision(
            conn,
            alert_identity=alert_identity,
            evidence_bundle_hash=evidence_bundle_hash,
            org_config_snapshot_hash=org_config_snapshot_hash,
        )
        if existing is not None:
            return AllocationResult(completed=existing, attempt=None)

        active = _fetch_non_terminal_for_alert(conn, alert_identity)
        if active is not None:
            existing_after_lock = fetch_completed_decision(
                conn,
                alert_identity=alert_identity,
                evidence_bundle_hash=evidence_bundle_hash,
                org_config_snapshot_hash=org_config_snapshot_hash,
            )
            if existing_after_lock is not None:
                return AllocationResult(
                    completed=existing_after_lock, attempt=None
                )
            msg = (
                f"non-terminal attempt {active.processing_attempt_identity!r} "
                f"already exists for alert {alert_identity!r}"
            )
            raise ActiveAttemptExistsError(msg)

        now = datetime.now(UTC).isoformat()
        cur = conn.execute(
            """
            INSERT INTO processing_attempts (
                alert_identity, evidence_bundle_hash, org_config_snapshot_hash,
                state, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alert_identity,
                evidence_bundle_hash,
                org_config_snapshot_hash,
                AttemptState.ALLOCATED.value,
                now,
                now,
            ),
        )
        if cur.lastrowid is None:
            msg = "INSERT did not return attempt_id"
            raise StateStoreError(msg)
        attempt_id = int(cur.lastrowid)
        attempt = _fetch_attempt_by_id(conn, _format_attempt_id(attempt_id))
        assert attempt is not None
        return AllocationResult(completed=None, attempt=attempt)


def transition_attempt(
    conn: sqlite3.Connection,
    processing_attempt_identity: str,
    new_state: AttemptState,
) -> ProcessingAttempt:
    """Transition attempt state along the lifecycle FSM."""
    with critical_transaction(conn):
        attempt = _fetch_attempt_by_id(conn, processing_attempt_identity)
        if attempt is None:
            msg = f"attempt not found: {processing_attempt_identity!r}"
            raise AttemptNotFoundError(msg)
        allowed = _ALLOWED_TRANSITIONS.get(attempt.state, frozenset())
        if new_state not in allowed:
            msg = (
                f"invalid transition {attempt.state.value!r} -> {new_state.value!r}"
            )
            raise InvalidTransitionError(msg)
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            UPDATE processing_attempts
            SET state = ?, updated_at = ?
            WHERE attempt_id = ?
            """,
            (new_state.value, now, int(processing_attempt_identity)),
        )
        updated = _fetch_attempt_by_id(conn, processing_attempt_identity)
        assert updated is not None
        return updated


def complete_attempt(
    conn: sqlite3.Connection,
    processing_attempt_identity: str,
) -> tuple[ProcessingAttempt, CompletedDecision]:
    """Mark attempt completed and insert completed-edict row."""
    with critical_transaction(conn):
        attempt = _fetch_attempt_by_id(conn, processing_attempt_identity)
        if attempt is None:
            msg = f"attempt not found: {processing_attempt_identity!r}"
            raise AttemptNotFoundError(msg)
        if attempt.state != AttemptState.READY_TO_APPEND:
            msg = "attempt must be ready_to_append before completion"
            raise InvalidTransitionError(msg)

        decision_id = derive_decision_id(
            attempt.alert_identity,
            attempt.evidence_bundle_hash,
            attempt.org_config_snapshot_hash,
            attempt.processing_attempt_identity,
        )
        completed = insert_completed_decision(
            conn,
            alert_identity=attempt.alert_identity,
            evidence_bundle_hash=attempt.evidence_bundle_hash,
            org_config_snapshot_hash=attempt.org_config_snapshot_hash,
            decision_id=decision_id,
            processing_attempt_identity=attempt.processing_attempt_identity,
        )
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            UPDATE processing_attempts
            SET state = ?, updated_at = ?
            WHERE attempt_id = ?
            """,
            (AttemptState.COMPLETED.value, now, int(processing_attempt_identity)),
        )
        finished = _fetch_attempt_by_id(conn, processing_attempt_identity)
        assert finished is not None
        return finished, completed


def abort_attempt(
    conn: sqlite3.Connection, processing_attempt_identity: str
) -> ProcessingAttempt:
    """Abort from any non-terminal state."""
    with critical_transaction(conn):
        attempt = _fetch_attempt_by_id(conn, processing_attempt_identity)
        if attempt is None:
            msg = f"attempt not found: {processing_attempt_identity!r}"
            raise AttemptNotFoundError(msg)
        if attempt.state in (AttemptState.COMPLETED, AttemptState.ABORTED):
            msg = f"cannot abort terminal attempt in state {attempt.state.value!r}"
            raise InvalidTransitionError(msg)
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            UPDATE processing_attempts
            SET state = ?, updated_at = ?
            WHERE attempt_id = ?
            """,
            (
                AttemptState.ABORTED.value,
                now,
                int(processing_attempt_identity),
            ),
        )
        updated = _fetch_attempt_by_id(conn, processing_attempt_identity)
        assert updated is not None
        return updated
