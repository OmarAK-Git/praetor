"""LLM judgment contract (proposed disposition only)."""

from __future__ import annotations

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1
from praetor.contracts.disposition import Disposition


class CitedEvidenceRef(ContractModel):
    evidence_id: str
    field_path: str


class ModelJudgment(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    proposed_disposition: Disposition
    cited_evidence_refs: list[CitedEvidenceRef]
    key_tells: list[str]
    org_config_refs: list[str]
    benign_alternatives: list[str]
    benign_alternatives_ruled_out: list[str]
    convergence_reasoning: str
    narrative: str
    model_name: str = Field(..., description="Model/provider metadata.")
    provider_name: str = Field(..., description="Model/provider metadata.")
