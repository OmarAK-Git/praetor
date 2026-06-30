"""Anchor-host scoping for correlated telemetry."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from praetor.correlation._event_fields import event_field, event_timestamp


def event_host_id(event: Mapping[str, Any]) -> str | None:
    """Return the Windows ``Computer`` host identifier for one raw event."""
    host = event_field(event, "Computer")
    if host is None:
        return None
    text = str(host).strip()
    return text or None


def _anchor_proximity_score(
    host: str,
    *,
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
    anchor_time: datetime | None,
) -> float:
    """Higher scores mean the host has events closer to ``anchor_time``."""
    if anchor_time is None:
        return 0.0
    min_delta = float("inf")
    for event in (*sysmon_events, *security_events):
        if event_host_id(event) != host:
            continue
        delta = abs((event_timestamp(event) - anchor_time).total_seconds())
        min_delta = min(min_delta, delta)
    if min_delta == float("inf"):
        return 0.0
    return -min_delta


def _anchor_host_rank(
    host: str,
    *,
    sysmon_by_host: Counter[str],
    security_by_host: Counter[str],
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
    anchor_time: datetime | None,
) -> tuple[int, int, int, float]:
    sysmon_count = sysmon_by_host[host]
    security_count = security_by_host[host]
    total = sysmon_count + security_count
    both_channels = int(sysmon_count > 0 and security_count > 0)
    proximity = _anchor_proximity_score(
        host,
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=anchor_time,
    )
    return (total, sysmon_count, both_channels, proximity)


def resolve_anchor_host_id(
    *,
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
    anchor_host_id: str | None = None,
    anchor_time: datetime | None = None,
) -> str | None:
    """Resolve the incident anchor host for correlation scoping.

    Explicit ``anchor_host_id`` wins. Otherwise choose the host with the
    strongest ordering-independent score:

    1. total in-window event count
    2. Sysmon event count
    3. presence on both Sysmon and Security channels
    4. closest event timestamp to ``anchor_time``

    When multiple hosts share the top rank, returns ``None`` so callers skip
    host filtering rather than pick an arbitrary winner.
    """
    if anchor_host_id is not None:
        explicit = anchor_host_id.strip()
        if explicit:
            return explicit

    sysmon_by_host: Counter[str] = Counter()
    security_by_host: Counter[str] = Counter()
    for event in sysmon_events:
        host = event_host_id(event)
        if host is not None:
            sysmon_by_host[host] += 1
    for event in security_events:
        host = event_host_id(event)
        if host is not None:
            security_by_host[host] += 1

    candidates = set(sysmon_by_host) | set(security_by_host)
    if not candidates:
        return None

    best_rank: tuple[int, int, int, float] | None = None
    winners: list[str] = []
    for host in candidates:
        rank = _anchor_host_rank(
            host,
            sysmon_by_host=sysmon_by_host,
            security_by_host=security_by_host,
            sysmon_events=sysmon_events,
            security_events=security_events,
            anchor_time=anchor_time,
        )
        if best_rank is None or rank > best_rank:
            best_rank = rank
            winners = [host]
        elif rank == best_rank:
            winners.append(host)

    if len(winners) != 1:
        return None
    return winners[0]


def filter_events_to_anchor_host(
    events: Sequence[Mapping[str, Any]],
    *,
    anchor_host_id: str,
) -> list[Mapping[str, Any]]:
    """Keep only events whose host matches ``anchor_host_id``."""
    return [
        event for event in events if event_host_id(event) == anchor_host_id
    ]
