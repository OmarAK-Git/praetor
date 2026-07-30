"""Correlation normalization for Windows telemetry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.correlation._event_fields import event_timestamp
from praetor.correlation.excerpts import build_correlation_prompt_excerpts
from praetor.correlation.host_isolation import (
    filter_events_to_anchor_host,
    resolve_anchor_host_id,
)
from praetor.correlation.security_log import (
    normalize_security_event,
    supports_security_event,
)
from praetor.correlation.sysmon import normalize_sysmon_event, supports_sysmon_event
from praetor.correlation.window import (
    DEFAULT_CORRELATION_WINDOW_SECONDS,
    filter_events_in_window,
)
from praetor.judgment.excerpt import PromptExcerptSet
from praetor.metrics.collector import MetricsCollector


@dataclass(frozen=True)
class CorrelationResult:
    bundle: EvidenceBundle
    prompt_excerpt_set: PromptExcerptSet


def correlate_telemetry(
    *,
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
    anchor_time: datetime,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
    anchor_host_id: str | None = None,
    metrics: MetricsCollector | None = None,
) -> CorrelationResult:
    """Normalize and window-filter telemetry into bundle + prompt excerpts."""
    filtered_sysmon = filter_events_in_window(
        list(sysmon_events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )
    filtered_security = filter_events_in_window(
        list(security_events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )

    resolved_anchor_host = resolve_anchor_host_id(
        sysmon_events=filtered_sysmon,
        security_events=filtered_security,
        anchor_host_id=anchor_host_id,
        anchor_time=anchor_time,
    )
    if resolved_anchor_host is not None:
        filtered_sysmon = filter_events_to_anchor_host(
            filtered_sysmon,
            anchor_host_id=resolved_anchor_host,
        )
        filtered_security = filter_events_to_anchor_host(
            filtered_security,
            anchor_host_id=resolved_anchor_host,
        )

    facts: list[EvidenceFact] = []
    for event in filtered_sysmon:
        if not supports_sysmon_event(event):
            if metrics is not None:
                metrics.record_correlation_unsupported_event_id()
            continue
        facts.append(normalize_sysmon_event(event))
    for event in filtered_security:
        if not supports_security_event(event):
            if metrics is not None:
                metrics.record_correlation_unsupported_event_id()
            continue
        facts.append(normalize_security_event(event))

    facts.sort(key=lambda fact: fact.timestamp)
    bundle = EvidenceBundle(facts=facts)
    return CorrelationResult(
        bundle=bundle,
        prompt_excerpt_set=build_correlation_prompt_excerpts(bundle),
    )


def load_fixture_events(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Load fixture file contents into a flat event list."""
    if isinstance(payload, Mapping) and "events" in payload:
        events = payload["events"]
        if not isinstance(events, list):
            msg = "fixture events must be a list"
            raise ValueError(msg)
        return [dict(item) for item in events]
    if isinstance(payload, Mapping):
        return [dict(payload)]
    return [dict(item) for item in payload]
