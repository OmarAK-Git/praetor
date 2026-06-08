"""Evidence bundle contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1


class EvidenceFact(ContractModel):
    """Normalized fact; normalized fields are source-specific."""

    evidence_id: str
    normalized_fields: dict[str, Any]
    source_event_reference: str
    raw_source: str
    provenance_path: str
    ambiguity_flag: bool
    timestamp: datetime
    entity_references: list[str] | None = None


class EvidenceBundle(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    facts: list[EvidenceFact]
