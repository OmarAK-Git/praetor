"""Windows Security log normalization."""

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
from praetor.correlation.ids import derive_evidence_id, source_event_reference
from praetor.evidence.provenance import WINDOWS_SECURITY_LOG

SECURITY_SUCCESSFUL_LOGON_EVENT_ID = 4624
SUPPORTED_SECURITY_EVENT_IDS = frozenset({SECURITY_SUCCESSFUL_LOGON_EVENT_ID})


def supports_security_event(event: Mapping[str, Any]) -> bool:
    event_id = int(event_field(event, "EventID") or 0)
    return event_id in SUPPORTED_SECURITY_EVENT_IDS


def normalize_security_event(event: Mapping[str, Any]) -> EvidenceFact:
    """Normalize one Windows Security event into an ``EvidenceFact``."""
    event_id = int(event_field(event, "EventID") or 0)
    if event_id != SECURITY_SUCCESSFUL_LOGON_EVENT_ID:
        msg = f"unsupported Security EventID: {event_id}"
        raise ValueError(msg)

    record_id = event_record_id(event)
    channel = str(event_field(event, "Channel") or "Security")
    source_ref = source_event_reference(
        channel=channel,
        event_id=event_id,
        record_id=record_id,
    )
    account_name = str(event_field(event, "TargetUserName") or "")
    domain = str(event_field(event, "TargetDomainName") or "")
    target_sid = str(event_field(event, "TargetSid") or "")
    host = str(event_field(event, "Computer") or "")

    normalized_fields: dict[str, Any] = {
        "account_name": account_name,
        "domain": domain,
        "target_sid": target_sid,
        "logon_type": str(event_field(event, "LogonType") or ""),
        "ip_address": str(event_field(event, "IpAddress") or ""),
        "host_id": host,
    }

    entity_references: list[str] = []
    if target_sid:
        entity_references.append(f"account:{target_sid}")
    if host:
        entity_references.append(f"host:{host.lower()}")

    ambiguity_flag = not target_sid or not account_name

    return EvidenceFact(
        evidence_id=derive_evidence_id(
            provenance_path=WINDOWS_SECURITY_LOG,
            source_event_reference=source_ref,
        ),
        normalized_fields=normalized_fields,
        source_event_reference=source_ref,
        raw_source=canonical_raw_source(event),
        provenance_path=WINDOWS_SECURITY_LOG,
        ambiguity_flag=ambiguity_flag,
        timestamp=event_timestamp(event),
        entity_references=entity_references or None,
    )
