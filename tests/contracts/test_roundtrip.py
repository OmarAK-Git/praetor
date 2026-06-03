"""Happy-path round-trip tests for all v1 contracts (B-002)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

from praetor.contracts.alert import AlertEnvelope
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.governance import AnalystAnnotation
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
)
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.policy import PolicyGateResult


def _roundtrip(model: BaseModel, model_type: type[BaseModel]) -> None:
    payload: dict[str, Any] = json.loads(model.model_dump_json())
    restored = model_type.model_validate(payload)
    assert restored == model


@pytest.mark.parametrize(
    ("fixture_name", "model_type"),
    [
        ("alert_envelope", AlertEnvelope),
        ("evidence_bundle", EvidenceBundle),
        ("org_config_snapshot", OrgConfigSnapshot),
        ("model_judgment", ModelJudgment),
        ("policy_gate_result", PolicyGateResult),
        ("decision_edict", DecisionEdict),
        ("containment_directive", ContainmentDirective),
        ("never_contain_snapshot_record", NeverContainSnapshotRecord),
        ("emergency_never_contain_record", EmergencyNeverContainRecord),
        ("directive_revocation_record", DirectiveRevocationRecord),
        ("revocation_feed_record", RevocationFeedRecord),
        ("system_health_alert", SystemHealthAlert),
        ("analyst_annotation", AnalystAnnotation),
        ("canonical_account_identity", CanonicalAccountIdentity),
    ],
)
def test_contract_roundtrip(
    fixture_name: str,
    model_type: type[BaseModel],
    request: pytest.FixtureRequest,
) -> None:
    model = request.getfixturevalue(fixture_name)
    _roundtrip(model, model_type)
