"""Stable evidence identifiers for normalized facts."""

from __future__ import annotations

from praetor.hashing.canonical import delimited, sha256_hex
from praetor.hashing.domains import DOMAIN_EVIDENCE_ID


def derive_evidence_id(*, provenance_path: str, source_event_reference: str) -> str:
    """Three-part SHA-256 per docs/contracts.md §3b; returns ``ev-`` + first 32 hex."""
    digest = sha256_hex(
        delimited([DOMAIN_EVIDENCE_ID, provenance_path, source_event_reference])
    )
    return f"ev-{digest[:32]}"


def source_event_reference(*, channel: str, event_id: int | str, record_id: str) -> str:
    channel_key = channel.split("/")[0].lower().replace(" ", "_")
    return f"{channel_key}:{event_id}:{record_id}"
