"""System health alert (outbox record, not in hash chain)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel

SchemaVersionV1 = Literal["1"]


class SystemHealthAlert(ContractModel):
    """Critical safety alert; full outbox delivery shape deferred to Task 8."""

    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    alert_code: str
    emitted_at: datetime
