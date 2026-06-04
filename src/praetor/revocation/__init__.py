"""Revocation feed export projection (delivery artifact, not audit authority)."""

from praetor.revocation.exporter import (
    FeedExportError,
    export_pending_feed_rows,
    is_feed_actuation_blocked,
    run_feed_startup_hook,
)
from praetor.revocation.feed import build_feed_record
from praetor.revocation.outbox import (
    FeedOutboxStatus,
    oldest_pending_feed_age_seconds,
    read_last_verified_exported_sequence,
)

__all__ = [
    "FeedExportError",
    "FeedOutboxStatus",
    "build_feed_record",
    "export_pending_feed_rows",
    "is_feed_actuation_blocked",
    "oldest_pending_feed_age_seconds",
    "read_last_verified_exported_sequence",
    "run_feed_startup_hook",
]
