"""V2-026 org-config numeric rate ceiling preflight tests."""

from __future__ import annotations

import pytest
from tests.config.helpers import preflight_document
from tests.config.shared import EXAMPLE_CONFIG

from praetor.config.errors import PreflightError
from praetor.config.loader import load_org_config_document
from praetor.config.preflight import DEFAULT_RATE_LIMIT_SCOPE_CEILING


def test_preflight_applies_default_ceilings_when_missing() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    assert "ceilings" not in doc["rate_limit_policy"]
    snapshot = preflight_document(doc)
    ceilings = snapshot.rate_limit_policy.ceilings
    assert ceilings.per_host == DEFAULT_RATE_LIMIT_SCOPE_CEILING
    assert ceilings.per_subnet == DEFAULT_RATE_LIMIT_SCOPE_CEILING
    assert ceilings.per_asset_group == DEFAULT_RATE_LIMIT_SCOPE_CEILING


def test_preflight_applies_default_for_partial_ceilings() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["rate_limit_policy"]["ceilings"] = {"per_host": 3}
    snapshot = preflight_document(doc)
    ceilings = snapshot.rate_limit_policy.ceilings
    assert ceilings.per_host == 3
    assert ceilings.per_subnet == DEFAULT_RATE_LIMIT_SCOPE_CEILING
    assert ceilings.per_asset_group == DEFAULT_RATE_LIMIT_SCOPE_CEILING


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("2", "must be an integer"),
        (0, "must be positive"),
        (-1, "must be positive"),
        (1.5, "must be an integer"),
    ],
)
def test_preflight_rejects_invalid_ceiling_values(value: object, message: str) -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["rate_limit_policy"]["ceilings"] = {
        "per_host": value,
        "per_subnet": 2,
        "per_asset_group": 2,
    }
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_rate_limits"
    assert message in str(exc.value)


def test_preflight_rejects_unknown_ceiling_scope() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["rate_limit_policy"]["ceilings"] = {
        "per_host": 1,
        "per_subnet": 1,
        "per_asset_group": 1,
        "per_org": 99,
    }
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_rate_limits"
    assert "per_org" in str(exc.value)


def test_preflight_accepts_explicit_ceilings() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["rate_limit_policy"]["ceilings"] = {
        "per_host": 5,
        "per_subnet": 10,
        "per_asset_group": 2,
    }
    snapshot = preflight_document(doc)
    ceilings = snapshot.rate_limit_policy.ceilings
    assert ceilings.per_host == 5
    assert ceilings.per_subnet == 10
    assert ceilings.per_asset_group == 2
