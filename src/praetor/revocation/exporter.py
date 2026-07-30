"""Sequential revocation-feed JSONL exporter and startup recovery.

Feed projection omits ``superseded_by_directive_id`` even when the ledger
revocation reason is supersession; consumers pair ``reason_code=supersession``
with replacement-directive metadata per ``docs/contracts.md`` §8.4.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from praetor.alerts.outbox import write_pending_health_alert
from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.ledger import DirectiveRevocationRecord
from praetor.metrics.collector import MetricsCollector
from praetor.revocation.feed import (
    FeedChecksumError,
    FeedPrefixIntegrityError,
    authoritative_feed_for_sequence,
    build_feed_record,
    feed_record_to_jsonl_line,
    feed_records_equivalent,
    find_verified_feed_line_for_sequence,
    validate_feed_file_prefix,
    verify_feed_jsonl_line,
)
from praetor.revocation.outbox import (
    FeedOutboxStatus,
    fetch_feed_outbox_row_extended,
    fetch_ledger_commit_at,
    has_feed_sequence_gap,
    increment_feed_export_retry,
    init_revocation_feed_export_schema,
    is_feed_unhealthy,
    mark_feed_row_exported,
    oldest_pending_feed_age_seconds,
    read_last_verified_exported_sequence,
    set_feed_unhealthy,
)
from praetor.state.sqlite_guard import critical_transaction

REVOCATION_FEED_UNHEALTHY_CODE = "revocation_feed_unhealthy"
FEED_FILE_SIZE_WARNING_CODE = "revocation_feed_file_size_warning"


class FeedExportError(Exception):
    """Non-recoverable feed export failure for a single row."""


class FeedJsonlSink(Protocol):
    """Append-only feed sink (v1: no rotation machinery)."""

    def append_line(self, line: str) -> None:
        """Append one canonical JSON line."""


@dataclass
class FileFeedJsonlSink:
    """Append-only JSONL file next to state DB."""

    path: Path

    def append_line(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


@dataclass(frozen=True)
class FeedExportResult:
    exported_count: int
    feed_unhealthy: bool
    degraded_actuation: bool


def default_feed_jsonl_path(db_path: Path) -> Path:
    return db_path.parent / "revocation_feed.jsonl"


def is_feed_actuation_blocked(
    conn: sqlite3.Connection,
    *,
    propagation_delay_seconds: int,
    now: datetime | None = None,
) -> bool:
    """Block new auto_contain when feed is unhealthy or pending exceeds SLO."""
    if is_feed_unhealthy(conn):
        return True
    age = oldest_pending_feed_age_seconds(conn, now=now)
    if age is None:
        return False
    return age > float(propagation_delay_seconds)


def _emit_feed_unhealthy_alert(conn: sqlite3.Connection) -> None:
    alert = SystemHealthAlert(
        alert_code=REVOCATION_FEED_UNHEALTHY_CODE,
        emitted_at=datetime.now(UTC),
    )
    write_pending_health_alert(conn, alert)


def check_feed_file_size_warning(
    conn: sqlite3.Connection,
    feed_path: Path,
    *,
    warning_bytes: int,
) -> bool:
    """Emit a health alert when the unrotated feed file crosses a size threshold.

    Purely observational: does not rotate, truncate, or otherwise modify the
    feed file, and does not affect ``is_feed_actuation_blocked``.
    """
    if not feed_path.exists():
        return False
    if feed_path.stat().st_size <= warning_bytes:
        return False
    alert = SystemHealthAlert(
        alert_code=FEED_FILE_SIZE_WARNING_CODE,
        emitted_at=datetime.now(UTC),
    )
    write_pending_health_alert(conn, alert)
    return True


def _transition_feed_unhealthy(conn: sqlite3.Connection) -> None:
    if is_feed_unhealthy(conn):
        return
    set_feed_unhealthy(conn, unhealthy=True)
    _emit_feed_unhealthy_alert(conn)
    conn.commit()


def _record_feed_export_lag_on_completion(
    conn: sqlite3.Connection,
    *,
    revocation_id: str,
    metrics: MetricsCollector | None,
    propagation_delay_seconds: int,
    export_completed_at: datetime,
) -> None:
    """Record per-export lag from ledger commit to verified feed write."""
    if metrics is None:
        return
    commit_at = fetch_ledger_commit_at(conn, revocation_id)
    if commit_at is None:
        return
    metrics.record_feed_export_lag(
        ledger_commit_at=commit_at,
        export_completed_at=export_completed_at,
        warning_threshold_seconds=float(propagation_delay_seconds),
    )


def _propagation_lag_seconds(
    conn: sqlite3.Connection,
    *,
    revocation_id: str,
    now: datetime | None = None,
) -> float | None:
    commit_at = fetch_ledger_commit_at(conn, revocation_id)
    if commit_at is None:
        return None
    reference = now if now is not None else datetime.now(UTC)
    return (reference - commit_at).total_seconds()


def _propagation_slo_missed(
    conn: sqlite3.Connection,
    *,
    revocation_id: str,
    propagation_delay_seconds: int,
    now: datetime | None = None,
) -> bool:
    lag = _propagation_lag_seconds(conn, revocation_id=revocation_id, now=now)
    return lag is not None and lag > float(propagation_delay_seconds)


def _mark_unhealthy_if_propagation_slo_missed(
    conn: sqlite3.Connection,
    *,
    revocation_id: str,
    propagation_delay_seconds: int,
    now: datetime | None = None,
) -> bool:
    if _propagation_slo_missed(
        conn,
        revocation_id=revocation_id,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
    ):
        _transition_feed_unhealthy(conn)
        return True
    return False


def _maybe_clear_feed_healthy(
    conn: sqlite3.Connection,
    *,
    propagation_delay_seconds: int,
    now: datetime | None = None,
) -> None:
    if not is_feed_unhealthy(conn):
        return
    if has_feed_sequence_gap(conn):
        return
    age = oldest_pending_feed_age_seconds(conn, now=now)
    if age is not None and age > float(propagation_delay_seconds):
        return
    set_feed_unhealthy(conn, unhealthy=False)
    conn.commit()


def _handle_feed_integrity_failure(conn: sqlite3.Connection) -> None:
    """Verification failures are hard failures (no retry budget)."""
    _transition_feed_unhealthy(conn)


def _handle_transient_export_failure(
    conn: sqlite3.Connection,
    *,
    sequence_number: int,
    max_feed_export_retries: int,
) -> None:
    with critical_transaction(conn):
        retries = increment_feed_export_retry(conn, sequence_number=sequence_number)
    conn.commit()
    if retries >= max_feed_export_retries:
        _transition_feed_unhealthy(conn)


def _feed_path_for_sink(sink: FeedJsonlSink) -> Path | None:
    if isinstance(sink, FileFeedJsonlSink):
        return sink.path
    return None


def reconcile_feed_metadata_against_jsonl(
    conn: sqlite3.Connection,
    feed_path: Path,
) -> bool:
    """Reconcile ``last_verified_exported_sequence`` against on-disk JSONL (AG-0030).

    Returns ``True`` when metadata matches the physical artifact. On mismatch
    (missing file, empty file, or truncated prefix vs metadata), marks the feed
    unhealthy and returns ``False``.
    """
    try:
        validate_feed_file_prefix(conn, feed_path)
    except FeedPrefixIntegrityError:
        _handle_feed_integrity_failure(conn)
        return False
    return True


def _ensure_feed_prefix_valid(conn: sqlite3.Connection, feed_path: Path | None) -> bool:
    if feed_path is None:
        return True
    return reconcile_feed_metadata_against_jsonl(conn, feed_path)


def _recover_verified_line_from_feed(
    conn: sqlite3.Connection,
    *,
    sequence_number: int,
    feed_path: Path,
    metrics: MetricsCollector | None = None,
    propagation_delay_seconds: int = 60,
    export_completed_at: datetime | None = None,
) -> bool:
    """Mark exported when JSONL already contains a verified line (crash recovery)."""
    verified = find_verified_feed_line_for_sequence(feed_path, sequence_number)
    if verified is None:
        return False
    row = fetch_feed_outbox_row_extended(conn, sequence_number)
    if row is None:
        msg = f"missing feed outbox row for sequence {sequence_number}"
        raise FeedExportError(msg)
    if verified.revocation_id != row.revocation_id:
        _handle_feed_integrity_failure(conn)
        return False
    authoritative = authoritative_feed_for_sequence(conn, sequence_number)
    if authoritative is None or not feed_records_equivalent(verified, authoritative):
        _handle_feed_integrity_failure(conn)
        return False
    with critical_transaction(conn):
        mark_feed_row_exported(conn, sequence_number=sequence_number)
    conn.commit()
    completed_at = (
        export_completed_at if export_completed_at is not None else datetime.now(UTC)
    )
    _record_feed_export_lag_on_completion(
        conn,
        revocation_id=row.revocation_id,
        metrics=metrics,
        propagation_delay_seconds=propagation_delay_seconds,
        export_completed_at=completed_at,
    )
    return True


def _export_row_to_sink(
    conn: sqlite3.Connection,
    *,
    sequence_number: int,
    sink: FeedJsonlSink,
) -> RevocationFeedRecord:
    row = fetch_feed_outbox_row_extended(conn, sequence_number)
    if row is None:
        msg = f"missing feed outbox row for sequence {sequence_number}"
        raise FeedExportError(msg)
    raw = conn.execute(
        "SELECT record_json FROM directive_revocation_records WHERE revocation_id = ?",
        (row.revocation_id,),
    ).fetchone()
    if raw is None:
        msg = f"missing revocation record for {row.revocation_id}"
        raise FeedExportError(msg)
    record = DirectiveRevocationRecord.model_validate_json(str(raw["record_json"]))
    feed = build_feed_record(record, sequence_number=sequence_number)
    line = feed_record_to_jsonl_line(feed)
    sink.append_line(line)
    feed_path = _feed_path_for_sink(sink)
    if feed_path is not None:
        written = feed_path.read_text(encoding="utf-8").strip().splitlines()[-1]
        verify_feed_jsonl_line(written)
    else:
        verify_feed_jsonl_line(line)
    return feed


def export_next_pending_row(
    conn: sqlite3.Connection,
    *,
    sink: FeedJsonlSink,
    max_feed_export_retries: int,
    propagation_delay_seconds: int = 60,
    now: datetime | None = None,
    metrics: MetricsCollector | None = None,
) -> bool:
    """Export one row in strict sequence order. Returns False when no work remains."""
    feed_path = _feed_path_for_sink(sink)
    if not _ensure_feed_prefix_valid(conn, feed_path):
        return False
    if has_feed_sequence_gap(conn):
        _transition_feed_unhealthy(conn)
        return False

    last_verified = read_last_verified_exported_sequence(conn)
    next_seq = last_verified + 1
    row = fetch_feed_outbox_row_extended(conn, next_seq)
    if row is None:
        return False
    if row.status == FeedOutboxStatus.EXPORTED:
        return False
    if row.status != FeedOutboxStatus.PENDING:
        return False

    if feed_path is not None and _recover_verified_line_from_feed(
        conn,
        sequence_number=next_seq,
        feed_path=feed_path,
        metrics=metrics,
        propagation_delay_seconds=propagation_delay_seconds,
        export_completed_at=now,
    ):
        row = fetch_feed_outbox_row_extended(conn, next_seq)
        slo_missed = False
        if row is not None:
            slo_missed = _mark_unhealthy_if_propagation_slo_missed(
                conn,
                revocation_id=row.revocation_id,
                propagation_delay_seconds=propagation_delay_seconds,
                now=now,
            )
        if not slo_missed and _ensure_feed_prefix_valid(conn, feed_path):
            _maybe_clear_feed_healthy(
                conn,
                propagation_delay_seconds=propagation_delay_seconds,
                now=now,
            )
        return True

    try:
        _export_row_to_sink(conn, sequence_number=next_seq, sink=sink)
    except FeedChecksumError:
        _handle_feed_integrity_failure(conn)
        return False
    except (FeedExportError, OSError):
        _handle_transient_export_failure(
            conn,
            sequence_number=next_seq,
            max_feed_export_retries=max_feed_export_retries,
        )
        return False

    with critical_transaction(conn):
        mark_feed_row_exported(conn, sequence_number=next_seq)
    conn.commit()
    completed_at = now if now is not None else datetime.now(UTC)
    _record_feed_export_lag_on_completion(
        conn,
        revocation_id=row.revocation_id,
        metrics=metrics,
        propagation_delay_seconds=propagation_delay_seconds,
        export_completed_at=completed_at,
    )
    slo_missed = _mark_unhealthy_if_propagation_slo_missed(
        conn,
        revocation_id=row.revocation_id,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
    )
    if not slo_missed and _ensure_feed_prefix_valid(conn, feed_path):
        _maybe_clear_feed_healthy(
            conn,
            propagation_delay_seconds=propagation_delay_seconds,
            now=now,
        )
    return True


def export_pending_feed_rows(
    conn: sqlite3.Connection,
    *,
    sink: FeedJsonlSink,
    max_feed_export_retries: int,
    propagation_delay_seconds: int = 60,
    now: datetime | None = None,
    metrics: MetricsCollector | None = None,
) -> FeedExportResult:
    """Drain pending rows in sequence until idle or unhealthy."""
    exported = 0
    while export_next_pending_row(
        conn,
        sink=sink,
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
        metrics=metrics,
    ):
        exported += 1
    unhealthy = is_feed_unhealthy(conn)
    degraded = is_feed_actuation_blocked(
        conn,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
    )
    return FeedExportResult(
        exported_count=exported,
        feed_unhealthy=unhealthy,
        degraded_actuation=degraded,
    )


def run_feed_startup_hook(
    conn: sqlite3.Connection,
    *,
    feed_path: Path,
    max_feed_export_retries: int,
    propagation_delay_seconds: int,
    now: datetime | None = None,
    metrics: MetricsCollector | None = None,
    feed_file_size_warning_bytes: int | None = None,
) -> FeedExportResult:
    """Recover pending feed rows before actuation; set degraded if SLO missed."""
    init_revocation_feed_export_schema(conn)
    if not reconcile_feed_metadata_against_jsonl(conn, feed_path):
        unhealthy = is_feed_unhealthy(conn)
        degraded = is_feed_actuation_blocked(
            conn,
            propagation_delay_seconds=propagation_delay_seconds,
            now=now,
        )
        return FeedExportResult(
            exported_count=0,
            feed_unhealthy=unhealthy,
            degraded_actuation=degraded,
        )
    sink = FileFeedJsonlSink(feed_path)
    result = export_pending_feed_rows(
        conn,
        sink=sink,
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
        metrics=metrics,
    )
    if is_feed_actuation_blocked(
        conn,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
    ):
        if not is_feed_unhealthy(conn):
            _transition_feed_unhealthy(conn)
        result = FeedExportResult(
            exported_count=result.exported_count,
            feed_unhealthy=True,
            degraded_actuation=True,
        )
    if feed_file_size_warning_bytes is not None:
        check_feed_file_size_warning(
            conn, feed_path, warning_bytes=feed_file_size_warning_bytes
        )
        conn.commit()
    return result


def run_feed_startup_hook_for_db(
    conn: sqlite3.Connection,
    db_path: Path,
    *,
    max_feed_export_retries: int = 3,
    propagation_delay_seconds: int = 60,
    metrics: MetricsCollector | None = None,
    feed_file_size_warning_bytes: int | None = None,
) -> FeedExportResult:
    """Default hook using feed path adjacent to the state database."""
    if feed_file_size_warning_bytes is None:
        from praetor.config.constants import DEFAULT_FEED_FILE_SIZE_WARNING_BYTES

        feed_file_size_warning_bytes = DEFAULT_FEED_FILE_SIZE_WARNING_BYTES
    return run_feed_startup_hook(
        conn,
        feed_path=default_feed_jsonl_path(db_path),
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        metrics=metrics,
        feed_file_size_warning_bytes=feed_file_size_warning_bytes,
    )
