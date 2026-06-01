"""Decision edict (authoritative completed decision record)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.policy import PolicyGateResult

SchemaVersionV1 = Literal["1"]
RecordTypeDecisionEdict = Literal["decision_edict"]


class DecisionEdict(ContractModel):
    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    record_type: RecordTypeDecisionEdict = "decision_edict"
    decision_id: str
    alert_reference: str
    evidence_bundle_hash: str
    org_config_snapshot_hash: str
    live_never_contain_hash: str
    model_judgment: ModelJudgment
    policy_gate_result: PolicyGateResult
    final_disposition: Disposition
    system_fault_escalation: bool
    fault_flags: list[str]
    stamp_status: str
    timing_metadata: dict[str, Any]
    ledger_previous_hash: str
    ledger_current_hash: str
    ticket_stamp_payload: dict[str, Any]
    containment_directive: ContainmentDirective | None = None
    decided_at: datetime = Field(..., description="Timing metadata anchor.")
