"""Revocation feed record construction and JSONL line integrity."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.ledger import DirectiveRevocationRecord
from praetor.hashing.canonical import CanonicalSerializationError, canonical_serialize
from praetor.hashing.domains import compute_feed_record_checksum
from praetor.revocation.outbox import (
    fetch_feed_outbox_row_extended,
    read_last_verified_exported_sequence,
)


class FeedChecksumError(ValueError):
    """Raised when a feed JSONL line fails checksum verification."""


class FeedPrefixIntegrityError(ValueError):
    """Raised when on-disk feed prefix is corrupt, out of order, or mismatched."""


def build_feed_record(
    record: DirectiveRevocationRecord,
    *,
    sequence_number: int,
    public_detail: str | None = None,
) -> RevocationFeedRecord:
    """Build a feed projection line with checksum (docs/contracts.md §8.1)."""
    body: dict[str, Any] = {
        "schema_version": "1",
        "sequence_number": sequence_number,
        "directive_id": record.directive_id,
        "revocation_id": record.revocation_id,
        "reason_code": record.reason_code,
        "revoked_at": record.revoked_at,
        "ledger_commit_at": record.ledger_commit_at,
        "public_detail": public_detail,
    }
    checksum = compute_feed_record_checksum(body)
    return RevocationFeedRecord(
        sequence_number=sequence_number,
        directive_id=record.directive_id,
        revocation_id=record.revocation_id,
        reason_code=record.reason_code,
        revoked_at=record.revoked_at,
        ledger_commit_at=record.ledger_commit_at,
        record_checksum=checksum,
        public_detail=public_detail,
    )


def feed_record_to_jsonl_line(record: RevocationFeedRecord) -> str:
    """Canonical JSON line for append-only feed (no rotation)."""
    # mode=python keeps timezone-aware datetimes for RFC3339 microsecond formatting.
    payload = record.model_dump(mode="python")
    return canonical_serialize(payload).decode("utf-8")


def verify_feed_jsonl_line(line: str) -> RevocationFeedRecord:
    """Verify checksum after read/write (corruption detection only)."""
    try:
        data: dict[str, Any] = json.loads(line)
        expected = str(data["record_checksum"])
        computed = compute_feed_record_checksum(data)
    except (KeyError, TypeError, ValidationError) as exc:
        msg = "feed line is not a valid RevocationFeedRecord shape"
        raise FeedChecksumError(msg) from exc
    if computed != expected:
        msg = "feed record_checksum mismatch after write"
        raise FeedChecksumError(msg)
    try:
        return RevocationFeedRecord.model_validate(data)
    except ValidationError as exc:
        msg = "feed line failed contract validation"
        raise FeedChecksumError(msg) from exc


def feed_records_equivalent(
    left: RevocationFeedRecord, right: RevocationFeedRecord
) -> bool:
    return left.model_dump(mode="json") == right.model_dump(mode="json")


def authoritative_feed_for_sequence(
    conn: sqlite3.Connection, sequence_number: int
) -> RevocationFeedRecord | None:
    """Build the authoritative feed projection for an assigned outbox sequence."""
    row = fetch_feed_outbox_row_extended(conn, sequence_number)
    if row is None:
        return None
    raw = conn.execute(
        "SELECT record_json FROM directive_revocation_records WHERE revocation_id = ?",
        (row.revocation_id,),
    ).fetchone()
    if raw is None:
        return None
    record = DirectiveRevocationRecord.model_validate_json(str(raw["record_json"]))
    return build_feed_record(record, sequence_number=sequence_number)


def _validate_prefix_lines(
    conn: sqlite3.Connection, lines: list[str]
) -> int:
    """Validate contiguous on-disk prefix; return highest sequence present."""
    expected_sequence = 1
    for line in lines:
        if not line.strip():
            continue
        try:
            on_disk = verify_feed_jsonl_line(line)
        except (
            FeedChecksumError,
            json.JSONDecodeError,
            CanonicalSerializationError,
            ValidationError,
        ) as exc:
            msg = "feed prefix line failed verification"
            raise FeedPrefixIntegrityError(msg) from exc
        if on_disk.sequence_number != expected_sequence:
            msg = (
                f"feed prefix sequence gap or reorder: expected "
                f"{expected_sequence}, found {on_disk.sequence_number}"
            )
            raise FeedPrefixIntegrityError(msg)
        authoritative = authoritative_feed_for_sequence(conn, expected_sequence)
        if authoritative is None:
            msg = f"feed prefix sequence {expected_sequence} has no outbox authority"
            raise FeedPrefixIntegrityError(msg)
        if not feed_records_equivalent(on_disk, authoritative):
            msg = "feed prefix line does not match authoritative revocation projection"
            raise FeedPrefixIntegrityError(msg)
        expected_sequence += 1
    return expected_sequence - 1


def validate_feed_file_prefix(conn: sqlite3.Connection, feed_path: Path) -> None:
    """Validate on-disk prefix and reconcile with export metadata."""
    last_verified = read_last_verified_exported_sequence(conn)
    if not feed_path.exists():
        if last_verified > 0:
            msg = "feed file missing but export metadata claims verified sequences"
            raise FeedPrefixIntegrityError(msg)
        return
    text = feed_path.read_text(encoding="utf-8").strip()
    if not text:
        if last_verified > 0:
            msg = "feed file empty but export metadata claims verified sequences"
            raise FeedPrefixIntegrityError(msg)
        return
    on_disk_highest = _validate_prefix_lines(conn, text.splitlines())
    if last_verified > on_disk_highest:
        msg = (
            f"feed file truncated: metadata last_verified={last_verified}, "
            f"on_disk_highest={on_disk_highest}"
        )
        raise FeedPrefixIntegrityError(msg)


def find_verified_feed_line_for_sequence(
    feed_path: Path, sequence_number: int
) -> RevocationFeedRecord | None:
    """Return a verified on-disk line for ``sequence_number``, if present."""
    if not feed_path.exists():
        return None
    text = feed_path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    for line in text.splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if int(data.get("sequence_number", -1)) != sequence_number:
            continue
        try:
            return verify_feed_jsonl_line(line)
        except (FeedChecksumError, ValidationError):
            return None
    return None
