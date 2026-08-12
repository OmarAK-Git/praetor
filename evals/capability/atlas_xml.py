"""Shared ATLAS Windows-Event XML helpers (Event-blob streaming)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

RE_EID = re.compile(rb"<EventID(?:\s[^>]*)?>(\d+)</EventID>", re.I)
RE_RID = re.compile(rb"<EventRecordID>(\d+)</EventRecordID>", re.I)
RE_TIME = re.compile(rb"SystemTime=['\"]([^'\"]+)['\"]")
RE_COMPUTER = re.compile(rb"<Computer>([^<]+)</Computer>", re.I)
RE_CHANNEL = re.compile(rb"<Channel>([^<]+)</Channel>", re.I)
RE_DATA = re.compile(rb"<Data Name=['\"]([^'\"]+)['\"]>([^<]*)</Data>", re.I)

CHUNK = 16 * 1024 * 1024
# Large carry: a single physical line may hold many <Event> blobs.
CARRY = 512 * 1024


def parse_ts(raw: bytes | None) -> datetime | None:
    if not raw:
        return None
    text = raw.decode("ascii", "ignore").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def iter_event_blobs(path: Path) -> Iterator[bytes]:
    """Yield complete ``<Event>...</Event>`` blobs (never line-oriented)."""
    with path.open("rb") as handle:
        head = handle.read(3)
        carry = b"" if head == b"\xef\xbb\xbf" else head
        while True:
            chunk = handle.read(CHUNK)
            if not chunk and not carry:
                break
            buf = carry + chunk
            pos = 0
            while True:
                start = buf.find(b"<Event", pos)
                if start < 0:
                    break
                if buf.startswith(b"<Events", start):
                    pos = start + 7
                    continue
                end = buf.find(b"</Event>", start)
                if end < 0:
                    break
                end += len(b"</Event>")
                yield buf[start:end]
                pos = end
            carry = buf[-CARRY:] if chunk else b""
            if not chunk:
                break


def parse_event_blob(blob: bytes) -> dict[str, object] | None:
    """Parse one Event blob into a flat dict + EventData mapping."""
    rid_m = RE_RID.search(blob)
    if not rid_m:
        return None
    eid_m = RE_EID.search(blob)
    ts_m = RE_TIME.search(blob)
    host_m = RE_COMPUTER.search(blob)
    ch_m = RE_CHANNEL.search(blob)
    data = {
        k.decode(): v.decode("utf-8", "ignore") for k, v in RE_DATA.findall(blob)
    }
    ts = parse_ts(ts_m.group(1) if ts_m else None)
    if ts is None:
        return None
    return {
        "EventID": int(eid_m.group(1)) if eid_m else 0,
        "EventRecordID": rid_m.group(1).decode(),
        "Channel": (
            ch_m.group(1).decode("utf-8", "ignore") if ch_m else ""
        ),
        "Computer": (
            host_m.group(1).decode("utf-8", "ignore") if host_m else ""
        ),
        "UtcTime": ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "timestamp": ts,
        "EventData": data,
    }


def find_event_by_record_id(path: Path, record_id: str) -> dict[str, object] | None:
    """Return the first Event blob matching EventRecordID."""
    want = record_id.encode("ascii")
    for blob in iter_event_blobs(path):
        rid_m = RE_RID.search(blob)
        if rid_m and rid_m.group(1) == want:
            return parse_event_blob(blob)
    return None
