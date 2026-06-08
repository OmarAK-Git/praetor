"""Containment directive integration contract."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, ValidationInfo, field_validator, model_validator

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1

DIRECTIVE_MAX_LIFETIME = timedelta(seconds=300)

# Windows SID form (docs/contracts.md §11); pattern not fully specified in docs.
_SID_PATTERN = re.compile(r"^S-1-5(?:-\d+)+$", re.IGNORECASE)


class DirectiveStatus(StrEnum):
    PROPOSED = "proposed"
    EMITTED = "emitted"


class TargetType(StrEnum):
    HOST = "host"
    ACCOUNT = "account"


class ContainmentDirective(ContractModel):
    """v1 integration directive.

    ``revocation_feed_id`` is reserved post-v1 and must not appear.
    """

    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    directive_id: str
    decision_id: str
    target_type: TargetType
    target_id: str
    scope: str
    evidence_refs: list[str]
    issued_at: datetime
    expires_at: datetime
    idempotency_key: str
    actuator_constraints: dict[str, Any]
    revocation_policy: dict[str, Any]
    status: DirectiveStatus
    live_never_contain_hash: str
    embedded_never_contain_entries: list[dict[str, Any]]
    minimum_feed_sequence_at_issue: int
    supersedes_directive_id: str | None = None

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": (
                "v1 containment directive. revocation_feed_id is reserved for post-v1 "
                "multi-feed deployments and must not be present."
            ),
        },
    )

    @field_validator("target_id")
    @classmethod
    def account_target_is_sid(cls, value: str, info: ValidationInfo) -> str:
        target_type = info.data.get("target_type")
        if target_type in (TargetType.ACCOUNT, TargetType.ACCOUNT.value):
            if not _SID_PATTERN.match(value):
                raise ValueError("account target_id must be a Windows SID form")
        return value

    @model_validator(mode="after")
    def validate_lifetime(self) -> ContainmentDirective:
        if self.expires_at - self.issued_at > DIRECTIVE_MAX_LIFETIME:
            raise ValueError("expires_at must be at most 300 seconds after issued_at")
        return self
