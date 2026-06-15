"""Shared telemetry event field extraction."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any


def event_field(event: Mapping[str, Any], *names: str) -> Any:
    """Return the first present field from the event or nested EventData."""
    event_data = event.get("EventData")
    nested: Mapping[str, Any] | None = (
        event_data if isinstance(event_data, Mapping) else None
    )
    for name in names:
        if name in event:
            return event[name]
        if nested is not None and name in nested:
            return nested[name]
    return None


def event_record_id(event: Mapping[str, Any]) -> str:
    record_id = event_field(event, "record_id", "RecordID", "EventRecordID")
    if record_id is None:
        msg = "telemetry event missing record identifier"
        raise ValueError(msg)
    return str(record_id)


def event_timestamp(event: Mapping[str, Any]) -> datetime:
    raw = event_field(event, "@timestamp", "UtcTime", "TimeCreated", "timestamp")
    if raw is None:
        msg = "telemetry event missing timestamp"
        raise ValueError(msg)
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=UTC)
        return raw.astimezone(UTC)
    text = str(raw).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def canonical_raw_source(event: Mapping[str, Any]) -> str:
    return json.dumps(dict(event), sort_keys=True, separators=(",", ":"), default=str)


def basename_path(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("/", "\\")
    if "\\" in text:
        return text.rsplit("\\", 1)[-1]
    return text
