"""Ticket stamp outbox and external integration (docs/plan.md Task 7)."""

from praetor.tickets.outbox import (
    StampOutboxEntry,
    StampStatus,
    TERMINAL_STAMP_STATUSES,
    ensure_stamp_outbox_schema,
    fetch_stamp_outbox,
    init_stamp_outbox_schema,
    record_stamp_outcome,
    write_pending_stamp,
)
from praetor.tickets.stamp import (
    NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK,
    StampBackendOutcome,
    StampBackendResult,
    StampContext,
    StampExecutionResult,
    StampTimeoutError,
    TicketStampBackend,
    execute_stamp,
)

__all__ = [
    "NON_IDEMPOTENT_BACKEND_DOUBLE_STAMP_RISK",
    "StampBackendOutcome",
    "StampBackendResult",
    "StampContext",
    "StampExecutionResult",
    "StampOutboxEntry",
    "StampStatus",
    "StampTimeoutError",
    "TERMINAL_STAMP_STATUSES",
    "TicketStampBackend",
    "ensure_stamp_outbox_schema",
    "execute_stamp",
    "fetch_stamp_outbox",
    "init_stamp_outbox_schema",
    "record_stamp_outcome",
    "write_pending_stamp",
]
