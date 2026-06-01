"""PolicyGate result shape (recording only; no gate implementation)."""

from __future__ import annotations

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1
from praetor.contracts.disposition import Disposition


class PolicyGateResult(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    proposed_disposition: Disposition
    final_disposition: Disposition
