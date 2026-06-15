"""Temporal filtering for correlated telemetry."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import TypeVar

T = TypeVar("T")

DEFAULT_CORRELATION_WINDOW_SECONDS = 300


def filter_events_in_window(
    events: Sequence[T],
    *,
    anchor_time: datetime,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
    timestamp_of: Callable[[T], datetime],
) -> list[T]:
    """Return events whose timestamps fall within ``anchor ± window_seconds``."""
    if window_seconds < 0:
        msg = "window_seconds must be non-negative"
        raise ValueError(msg)
    start = anchor_time - timedelta(seconds=window_seconds)
    end = anchor_time + timedelta(seconds=window_seconds)
    return [
        event
        for event in events
        if start <= timestamp_of(event) <= end
    ]
