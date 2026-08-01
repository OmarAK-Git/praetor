"""Path B bundle assembly for the capability spike.

Windowing and anchor-host filtering reuse the real correlation helpers so the
ONLY difference between Path A and Path B is event-type coverage. Do not
reimplement either filter here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from evals.capability.flatten import flatten_event_to_fact, resolve_provenance_path
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.correlation._event_fields import event_timestamp
from praetor.correlation.host_isolation import filter_events_to_anchor_host
from praetor.correlation.window import (
    DEFAULT_CORRELATION_WINDOW_SECONDS,
    filter_events_in_window,
)


def _datable(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Drop events without a parseable timestamp or record id."""
    usable: list[Mapping[str, Any]] = []
    for event in events:
        try:
            event_timestamp(event)
        except (ValueError, TypeError):
            continue
        usable.append(event)
    return usable


def build_spike_bundle(
    events: Sequence[Mapping[str, Any]],
    *,
    anchor_time: datetime,
    anchor_host_id: str | None = None,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
) -> EvidenceBundle:
    """Build an all-event-type bundle scoped exactly as correlation would."""
    windowed = filter_events_in_window(
        _datable(events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )
    if anchor_host_id is not None:
        windowed = filter_events_to_anchor_host(
            windowed, anchor_host_id=anchor_host_id
        )

    facts: list[EvidenceFact] = []
    for event in windowed:
        try:
            facts.append(
                flatten_event_to_fact(
                    event, provenance_path=resolve_provenance_path(event)
                )
            )
        except (ValueError, TypeError):
            continue
    return EvidenceBundle(facts=facts)
