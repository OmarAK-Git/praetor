"""Generic Windows-event flattener for capability-spike Path B.

Correlation normalizes only Sysmon EventID 1 and Security 4624
(``correlation/sysmon.py:23``, ``correlation/security_log.py:19``). This
module produces an ``EvidenceFact`` from ANY event so Path B can measure
what judgment does with full evidence coverage.

Deliberately dumb: it flattens whatever fields are present and adds no
per-event-type interpretation. Hand-tuned extraction here would mean a good
Path B score measures this file rather than Praetor.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from praetor.contracts.evidence import EvidenceFact
from praetor.correlation._event_fields import (
    canonical_raw_source,
    event_field,
    event_record_id,
    event_timestamp,
)
from praetor.correlation.host_isolation import event_host_id
from praetor.correlation.ids import derive_evidence_id, source_event_reference
from praetor.evidence.provenance import SYSMON_EVENT_LOG, WINDOWS_SECURITY_LOG

SPIKE_UNKNOWN_SOURCE = "spike_unknown_source"
_RAW_SOURCE_KEY = "raw_source"
_STRUCTURAL_KEYS = frozenset({"EventData", _RAW_SOURCE_KEY})


def resolve_provenance_path(event: Mapping[str, Any]) -> str:
    """Map an event to a provenance path by SOURCE, not by event type.

    Corroboration counts distinct provenance paths, so every Sysmon EventID
    collapses to one path by design.
    """
    channel = str(event_field(event, "Channel") or "")
    lowered = channel.lower()
    if "sysmon" in lowered:
        return SYSMON_EVENT_LOG
    if lowered.startswith("security"):
        return WINDOWS_SECURITY_LOG
    return SPIKE_UNKNOWN_SOURCE


def _flatten_fields(event: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in event.items():
        if key in _STRUCTURAL_KEYS:
            continue
        flattened[str(key)] = value
    nested = event.get("EventData")
    if isinstance(nested, Mapping):
        for key, value in nested.items():
            if key == _RAW_SOURCE_KEY:
                continue
            flattened[str(key)] = value
    return flattened


def flatten_event_to_fact(
    event: Mapping[str, Any],
    *,
    provenance_path: str,
) -> EvidenceFact:
    """Build an ``EvidenceFact`` from any Windows event dict."""
    record_id = event_record_id(event)
    event_id = event_field(event, "EventID") or 0
    channel = str(event_field(event, "Channel") or "unknown")
    source_ref = source_event_reference(
        channel=channel,
        event_id=event_id,
        record_id=record_id,
    )

    normalized_fields = _flatten_fields(event)
    normalized_fields["host_id"] = event_host_id(event) or ""

    return EvidenceFact(
        evidence_id=derive_evidence_id(
            provenance_path=provenance_path,
            source_event_reference=source_ref,
        ),
        normalized_fields=normalized_fields,
        source_event_reference=source_ref,
        raw_source=canonical_raw_source(event),
        provenance_path=provenance_path,
        ambiguity_flag=False,
        timestamp=event_timestamp(event),
        entity_references=None,
    )
