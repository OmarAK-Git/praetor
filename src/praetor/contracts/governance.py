"""Analyst annotation (human governance loop)."""

from __future__ import annotations

from datetime import datetime
from pydantic import model_validator

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1
from praetor.contracts.disposition import Disposition


class AnalystAnnotation(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    disposition_correct: bool
    corrected_disposition: Disposition | None = None
    comment: str
    reviewer_identity: str
    timestamp: datetime

    @model_validator(mode="after")
    def validate_correction(self) -> AnalystAnnotation:
        if not self.disposition_correct:
            if self.corrected_disposition is None:
                raise ValueError("corrected_disposition is required when disposition_correct is false")
        elif self.corrected_disposition is not None:
            raise ValueError("corrected_disposition must be null when disposition_correct is true")
        return self
