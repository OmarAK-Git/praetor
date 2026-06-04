"""Sequential revocation-feed JSONL exporter and startup recovery."""

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


def _transition_feed_unhealthy(conn: sqlite3.Connection) -> None:
    if is_feed_unhealthy(conn):
        return
    set_feed_unhealthy(conn, unhealthy=True)
    _emit_feed_unhealthy_alert(conn)
    conn.commit()


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


def _ensure_feed_prefix_valid(conn: sqlite3.Connection, feed_path: Path | None) -> bool:
    if feed_path is None:
        return True
    try:
        validate_feed_file_prefix(conn, feed_path)
    except FeedPrefixIntegrityError:
        _handle_feed_integrity_failure(conn)
        return False
    return True


def _recover_verified_line_from_feed(
    conn: sqlite3.Connection,
    *,
    sequence_number: int,
    feed_path: Path,
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
        conn, sequence_number=next_seq, feed_path=feed_path
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
) -> FeedExportResult:
    """Drain pending rows in sequence until idle or unhealthy."""
    exported = 0
    while export_next_pending_row(
        conn,
        sink=sink,
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
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
) -> FeedExportResult:
    """Recover pending feed rows before actuation; set degraded if SLO missed."""
    init_revocation_feed_export_schema(conn)
    sink = FileFeedJsonlSink(feed_path)
    result = export_pending_feed_rows(
        conn,
        sink=sink,
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
        now=now,
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
    return result


def run_feed_startup_hook_for_db(
    conn: sqlite3.Connection,
    db_path: Path,
    *,
    max_feed_export_retries: int = 3,
    propagation_delay_seconds: int = 60,
) -> FeedExportResult:
    """Default hook using feed path adjacent to the state database."""
    return run_feed_startup_hook(
        conn,
        feed_path=default_feed_jsonl_path(db_path),
        max_feed_export_retries=max_feed_export_retries,
        propagation_delay_seconds=propagation_delay_seconds,
    )
