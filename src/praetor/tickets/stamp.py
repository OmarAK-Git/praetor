"""Ticket stamp orchestration — pending outbox, backend call, durable outcome.

Non-idempotent ticket backends cannot guarantee that resending the same ``stamp_id``
after an ``unknown`` outcome is a no-op. Where the receiver is not idempotent,
recovery retry carries residual **double-stamp** risk; operators must use an
idempotent integration or accept duplicate ticket creation on ambiguous timeouts.
See ``docs/spec.md`` § Ticket Stamp Contract and Outbox.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from praetor.hashing import derive_stamp_id
from praetor.tickets.outbox import (
    TERMINAL_STAMP_STATUSES,
    StampOutboxEntry,
    StampStatus,
    fetch_stamp_outbox,
    record_stamp_outcome,
    write_pending_stamp,
)

NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK = (
    "Ticket backends that are not idempotent on stamp_id carry residual "
    "double-stamp risk: retry after unknown may create duplicate tickets; "
    "v1 assumes idempotent receivers."
)


class StampBackendOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class StampBackendResult:
    outcome: StampBackendOutcome
    payload: dict[str, Any] | None = None


class StampTimeoutError(Exception):
    """Raised when the ticket system times out or returns an ambiguous response."""


def _is_backend_ambiguity(exc: BaseException) -> bool:
    """True for transport/timeout/ambiguous backend faults, not programmer bugs."""
    if isinstance(exc, StampTimeoutError | ConnectionError | TimeoutError):
        return True
    if isinstance(exc, OSError) and not isinstance(
        exc,
        FileNotFoundError
        | PermissionError
        | IsADirectoryError
        | NotADirectoryError,
    ):
        return True
    return False


class TicketStampBackend(Protocol):
    """External ticket integration; must treat repeated stamp_id as idempotent."""

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        """Stamp or replay; duplicate stamp_id should be an idempotent no-op."""


@dataclass(frozen=True)
class StampContext:
    alert_identity: str
    evidence_bundle_hash: str
    org_config_snapshot_hash: str
    processing_attempt_identity: str
    ticket_payload: dict[str, Any]


@dataclass(frozen=True)
class StampExecutionResult:
    stamp_id: str
    status: StampStatus
    ticket_payload: dict[str, Any]
    response_payload: dict[str, Any] | None


def _to_execution_result(entry: StampOutboxEntry) -> StampExecutionResult:
    return StampExecutionResult(
        stamp_id=entry.stamp_id,
        status=entry.status,
        ticket_payload=entry.ticket_payload,
        response_payload=entry.response_payload,
    )


def execute_stamp(
    conn: sqlite3.Connection,
    backend: TicketStampBackend,
    context: StampContext,
) -> StampExecutionResult:
    """Write pending outbox (if needed), call backend, record durable outcome.

    Recovery on ``unknown`` resends the same ``stamp_id`` without creating a new
    outbox row. Terminal ``succeeded`` / ``failed`` rows are returned as-is.
    """
    stamp_id = derive_stamp_id(
        context.alert_identity,
        context.evidence_bundle_hash,
        context.org_config_snapshot_hash,
    )
    existing = fetch_stamp_outbox(conn, stamp_id)
    if existing is not None and existing.status in TERMINAL_STAMP_STATUSES:
        if existing.status != StampStatus.UNKNOWN:
            return _to_execution_result(existing)

    ticket_payload = context.ticket_payload
    if existing is None:
        write_pending_stamp(
            conn,
            stamp_id=stamp_id,
            alert_identity=context.alert_identity,
            evidence_bundle_hash=context.evidence_bundle_hash,
            org_config_snapshot_hash=context.org_config_snapshot_hash,
            processing_attempt_identity=context.processing_attempt_identity,
            ticket_payload=ticket_payload,
        )
    else:
        ticket_payload = existing.ticket_payload

    try:
        backend_result = backend.stamp(stamp_id, ticket_payload)
    except BaseException as exc:
        if _is_backend_ambiguity(exc):
            entry = record_stamp_outcome(conn, stamp_id, StampStatus.UNKNOWN, None)
            return _to_execution_result(entry)
        raise

    if backend_result.outcome == StampBackendOutcome.SUCCEEDED:
        status = StampStatus.SUCCEEDED
    else:
        status = StampStatus.FAILED

    entry = record_stamp_outcome(conn, stamp_id, status, backend_result.payload)
    return _to_execution_result(entry)
