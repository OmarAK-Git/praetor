"""Canonical account identity."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel

SchemaVersionV1 = Literal["1"]


class CanonicalAccountIdentity(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    sid: str = Field(..., description="Security identifier (SID).")
    domain: str
    account_name: str
    account_type: str
    authority_source: str
    ambiguity_flag: bool
