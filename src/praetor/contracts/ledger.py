"""Hash-chain ledger record types (four distinct record_type values)."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal

from pydantic import model_validator

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel

SchemaVersionV1 = Literal["1"]

EMERGENCY_MAX_LIFETIME = timedelta(hours=48)

RecordTypeNeverContainSnapshot = Literal["never_contain_snapshot"]
RecordTypeEmergencyNeverContain = Literal["emergency_never_contain"]
RecordTypeDirectiveRevocation = Literal["directive_revocation"]


class RevocationReason(str, Enum):
    """Internal revocation reason (ledger); maps to external reason_code."""

    SUPERSESSION = "supersession"
    NEVER_CONTAIN_CONFLICT = "never_contain_conflict"
    MANUAL = "manual"
    POST_ACTIVATION_RECONCILIATION = "post_activation_reconciliation"


class NeverContainSnapshotRecord(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    record_type: RecordTypeNeverContainSnapshot = "never_contain_snapshot"
    snapshot_id: str
    snapshot_hash: str
    snapshot_content: list[dict[str, Any]]
    evaluated_at: datetime
    triggered_by_decision_id: str


class EmergencyNeverContainRecord(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    record_type: RecordTypeEmergencyNeverContain = "emergency_never_contain"
    entry_id: str
    target_specification: dict[str, Any]
    added_by: str
    added_at: datetime
    expires_at: datetime
    audit_reason: str

    @model_validator(mode="after")
    def validate_lifetime(self) -> EmergencyNeverContainRecord:
        if self.expires_at - self.added_at > EMERGENCY_MAX_LIFETIME:
            raise ValueError("expires_at must be at most 48 hours after added_at")
        return self


class DirectiveRevocationRecord(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    record_type: RecordTypeDirectiveRevocation = "directive_revocation"
    revocation_id: str
    directive_id: str
    reason: RevocationReason
    reason_code: str
    triggered_by: str
    revoked_at: datetime
    ledger_commit_at: datetime
    idempotency_key_cleared: bool
    superseded_by_directive_id: str | None = None

    @model_validator(mode="after")
    def validate_cross_fields(self) -> DirectiveRevocationRecord:
        if self.reason == RevocationReason.SUPERSESSION:
            if self.superseded_by_directive_id is None:
                raise ValueError(
                    "superseded_by_directive_id is required when reason is supersession"
                )
        elif self.superseded_by_directive_id is not None:
            raise ValueError(
                "superseded_by_directive_id must be null unless reason is supersession"
            )
        # docs/contracts.md §11: cleared only for SOC-lead manual revocation (RevocationReason.MANUAL).
        if self.idempotency_key_cleared and self.reason != RevocationReason.MANUAL:
            raise ValueError(
                "idempotency_key_cleared may be true only when reason is manual revocation"
            )
        return self
