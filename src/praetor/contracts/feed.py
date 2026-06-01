"""Revocation feed projection line (delivery artifact, not audit authority)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel

SchemaVersionV1 = Literal["1"]


class RevocationFeedRecord(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    sequence_number: int
    directive_id: str
    revocation_id: str
    reason_code: str
    revoked_at: datetime
    ledger_commit_at: datetime
    record_checksum: str = Field(
        ...,
        description="Corruption detection only; computed per docs/contracts.md (Task 3).",
    )
    public_detail: str | None = None
