"""System health alert (outbox record, not in hash chain)."""

from __future__ import annotations

from datetime import datetime

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1


class SystemHealthAlert(ContractModel):
    """Critical safety alert emission payload (outbox record, not in hash chain).

    Durable delivery and per-channel status tracking live in the SQLite outbox
    (Task 8: ``system_health_alert_outbox`` / ``system_health_delivery_attempts``),
    not as fields on this contract. See ``docs/spec.md`` § SystemHealthAlert
    Delivery.
    """

    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    alert_code: str
    emitted_at: datetime
