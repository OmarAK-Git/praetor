"""Shared contract conventions (strict Pydantic v2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

SchemaVersionV1 = Literal["1"]
SCHEMA_VERSION_V1: SchemaVersionV1 = "1"

# extra=forbid rejects unknown keys; strict=False allows JSON round-trip coercion
# (datetime strings, enum values) while keeping typed models in Python.
CONTRACT_CONFIG = ConfigDict(extra="forbid")


class ContractModel(BaseModel):
    """Base for all versioned integration and ledger contracts."""

    model_config = CONTRACT_CONFIG


def roundtrip_dict(model: ContractModel) -> dict[str, Any]:
    """Serialize to JSON-compatible dict and validate back."""
    return model.model_dump(mode="json")
