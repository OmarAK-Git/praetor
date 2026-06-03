"""OrgConfigSnapshot contract validation (Task 9 typed sections)."""

from __future__ import annotations

import pytest
import yaml
from tests.config.helpers import preflight_path
from tests.config.shared import EXAMPLE_CONFIG

from praetor.config.errors import PreflightError
from praetor.config.loader import load_org_config_document
from praetor.config.preflight import run_preflight
from praetor.contracts.org_config import OrgConfigSnapshot


def test_example_config_roundtrips_through_contract() -> None:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    restored = OrgConfigSnapshot.model_validate_json(snapshot.model_dump_json())
    assert restored.snapshot_hash == snapshot.snapshot_hash


def test_missing_subnet_membership_rejected_at_preflight() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["assets_and_asset_groups"]["entries"][0] = {"asset_id": "bad"}
    with pytest.raises(PreflightError):
        run_preflight(doc, verbatim_text=yaml.dump(doc))


def test_extra_top_level_field_rejected_by_contract_build() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["rogue"] = True
    with pytest.raises(PreflightError) as exc:
        run_preflight(doc, verbatim_text=yaml.dump(doc))
    assert exc.value.code == "unknown_top_level_key"
