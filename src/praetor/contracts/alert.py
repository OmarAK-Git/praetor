"""Alert intake contract."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel

SchemaVersionV1 = Literal["1"]


class AlertEnvelope(ContractModel):
    """Versioned alert at intake; ``alert_identity`` is the SOC-assigned reference."""

    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    alert_identity: str = Field(
        ...,
        description="Stable upstream alert reference (not Praetor attempt/queue ids).",
    )
