"""Sysmon telemetry normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from praetor.contracts.evidence import EvidenceFact
from praetor.correlation._event_fields import (
    basename_path,
    canonical_raw_source,
    event_field,
    event_record_id,
    event_timestamp,
)
from praetor.correlation.ids import derive_evidence_id, source_event_reference
from praetor.evidence.provenance import SYSMON_EVENT_LOG

SYSMON_PROCESS_CREATE_EVENT_ID = 1
SUPPORTED_SYSMON_EVENT_IDS = frozenset({SYSMON_PROCESS_CREATE_EVENT_ID})


def supports_sysmon_event(event: Mapping[str, Any]) -> bool:
    event_id = int(event_field(event, "EventID") or 0)
    return event_id in SUPPORTED_SYSMON_EVENT_IDS


def normalize_sysmon_event(event: Mapping[str, Any]) -> EvidenceFact:
    """Normalize one Sysmon event into an ``EvidenceFact``."""
    event_id = int(event_field(event, "EventID") or 0)
    if event_id != SYSMON_PROCESS_CREATE_EVENT_ID:
        msg = f"unsupported Sysmon EventID: {event_id}"
        raise ValueError(msg)

    record_id = event_record_id(event)
    channel = str(
        event_field(event, "Channel") or "Microsoft-Windows-Sysmon/Operational"
    )
    source_ref = source_event_reference(
        channel=channel,
        event_id=event_id,
        record_id=record_id,
    )
    process_guid = str(event_field(event, "ProcessGuid") or "")
    parent_process_guid = str(event_field(event, "ParentProcessGuid") or "")
    parent_image = event_field(event, "ParentImage")
    user = str(event_field(event, "User") or "")
    image = str(event_field(event, "Image") or "")
    command_line = str(event_field(event, "CommandLine") or "")
    host = str(event_field(event, "Computer") or "")

    normalized_fields: dict[str, Any] = {
        "process_name": basename_path(image) or "",
        "image": image,
        "command_line": command_line,
        "user": user,
        "process_guid": process_guid,
        "process_id": str(event_field(event, "ProcessId") or ""),
        "parent_process_guid": parent_process_guid,
        "parent_process_id": str(event_field(event, "ParentProcessId") or ""),
        "parent_image": str(parent_image or ""),
        "parent_process_name": basename_path(parent_image) or "",
        "host_id": host,
    }

    entity_references = _entity_references(
        process_guid=process_guid,
        parent_process_guid=parent_process_guid,
        host=host,
        user=user,
    )
    ambiguity_flag = _sysmon_ambiguity_flag(
        user=user,
        parent_process_guid=parent_process_guid,
        parent_image=parent_image,
    )

    return EvidenceFact(
        evidence_id=derive_evidence_id(
            provenance_path=SYSMON_EVENT_LOG,
            source_event_reference=source_ref,
        ),
        normalized_fields=normalized_fields,
        source_event_reference=source_ref,
        raw_source=canonical_raw_source(event),
        provenance_path=SYSMON_EVENT_LOG,
        ambiguity_flag=ambiguity_flag,
        timestamp=event_timestamp(event),
        entity_references=entity_references,
    )


def _entity_references(
    *,
    process_guid: str,
    parent_process_guid: str,
    host: str,
    user: str,
) -> list[str]:
    refs: list[str] = []
    if process_guid:
        refs.append(f"process:{process_guid}")
    if parent_process_guid:
        refs.append(f"process:{parent_process_guid}")
    if host:
        refs.append(f"host:{host.lower()}")
    if "\\" in user:
        refs.append(f"user:{user.lower()}")
    return refs


def _sysmon_ambiguity_flag(
    *,
    user: str,
    parent_process_guid: str,
    parent_image: Any,
) -> bool:
    if user and "\\" not in user:
        return True
    if parent_image and not parent_process_guid:
        return True
    return False
