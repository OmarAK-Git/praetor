"""Task 9 — org config loader, preflight, snapshot hash."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from tests.config.helpers import preflight_document, preflight_loaded, preflight_path
from tests.config.shared import EXAMPLE_CONFIG, EXAMPLE_SNAPSHOT_HASH, SOC_LEAD_TOKEN

from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.constants import HARD_CONFIG_CHARACTER_BUDGET
from praetor.config.errors import ActivationError, ConfigLoadError, PreflightError
from praetor.config.loader import load_org_config_document, load_org_config_source
from praetor.config.preflight import apply_field_defaults
from praetor.config.snapshot import (
    reject_unknown_top_level_keys,
    verbatim_character_count,
)
from praetor.hashing import ORG_CONFIG_SNAPSHOT_HASH_KEYS
from praetor.state.store import open_state_store


def test_valid_config_loads_stable_snapshot_hash() -> None:
    first = preflight_path(EXAMPLE_CONFIG)
    second = preflight_path(EXAMPLE_CONFIG)
    assert first.snapshot_hash == second.snapshot_hash
    assert first.snapshot_hash == EXAMPLE_SNAPSHOT_HASH
    body = first.model_dump(mode="json")
    body.pop("snapshot_hash")
    assert set(body.keys()) == set(ORG_CONFIG_SNAPSHOT_HASH_KEYS)


def test_missing_required_section_fails_preflight() -> None:
    loaded = load_org_config_source(EXAMPLE_CONFIG)
    del loaded.document["business_context"]
    with pytest.raises(PreflightError) as exc:
        preflight_loaded(loaded)
    assert exc.value.code == "missing_section"


def test_unknown_top_level_key_fails_and_affects_budget() -> None:
    loaded = load_org_config_source(EXAMPLE_CONFIG)
    doc = loaded.document
    doc["rogue_section"] = {"x": 1}
    with pytest.raises(PreflightError) as exc:
        reject_unknown_top_level_keys(doc)
    assert exc.value.code == "unknown_top_level_key"

    base_count = verbatim_character_count(loaded.verbatim_text)
    padded = loaded.verbatim_text + "\n# padding\n" + ("y" * 5000)
    assert verbatim_character_count(padded) > base_count


def test_config_over_budget_fails_preflight(tmp_path: Path) -> None:
    loaded = load_org_config_source(EXAMPLE_CONFIG)
    doc = loaded.document
    doc["business_context"] = {"notes": "x" * (HARD_CONFIG_CHARACTER_BUDGET + 100)}
    path = tmp_path / "big.yaml"
    path.write_text(yaml.dump(doc), encoding="utf-8")
    big = load_org_config_source(path)
    with pytest.raises(PreflightError) as exc:
        preflight_loaded(big)
    assert exc.value.code == "config_over_budget"


def test_activation_error_preserves_preflight_code(
    tmp_path: Path, verifier: PrincipalMapVerifier
) -> None:
    loaded = load_org_config_source(EXAMPLE_CONFIG)
    doc = loaded.document
    doc["business_context"] = {"notes": "x" * (HARD_CONFIG_CHARACTER_BUDGET + 50)}
    path = tmp_path / "big.yaml"
    path.write_text(yaml.dump(doc), encoding="utf-8")
    s = open_state_store(tmp_path / "s.db")
    try:
        with pytest.raises(ActivationError) as exc:
            activate_org_config(
                s,
                path,
                token=SOC_LEAD_TOKEN,
                verifier=verifier,
            )
        assert exc.value.code == "config_over_budget"
    finally:
        s.close()


def test_duplicate_yaml_keys_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.yaml"
    path.write_text(
        "version_metadata:\n  org_id: a\n  config_version: '1'\n"
        "version_metadata:\n  org_id: b\n  config_version: '2'\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="duplicate"):
        load_org_config_document(path)


def test_containment_conflict_without_precedence_fails() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"] = {
        "default_action": "escalate",
        "rules": [
            {"name": "a", "action": "allow", "scope": {"catch_all": True}},
            {"name": "b", "action": "deny", "scope": {"catch_all": True}},
        ]
    }
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "containment_policy_conflict"


def test_string_scope_global_fails_preflight() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"]["rules"] = [
        {"name": "default_escalate", "action": "escalate", "scope": "global"},
    ]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_containment_rule_scope"


@pytest.mark.parametrize(
    "scope",
    [
        {"catch_all": False},
        {"catch_all": True, "target_type": "host", "target_id": "ws-01"},
    ],
    ids=["catch_all_false", "mixed_scope_keys"],
)
def test_malformed_object_scope_fails_preflight(scope: dict[str, object]) -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"]["rules"] = [
        {"name": "broken_scope", "action": "escalate", "scope": scope},
    ]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_containment_rule_scope"


def test_unknown_containment_rule_key_rejected() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"]["rules"] = [
        {
            "name": "bad",
            "action": "escalate",
            "scope": {"catch_all": True},
            "rogue_key": True,
        },
    ]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_containment_policy"


def test_unknown_containment_policy_key_rejected() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"]["extra_section"] = True
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_containment_policy"


def test_containment_rule_scopes_round_trip() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"] = {
        "default_action": "escalate",
        "precedence": ["deny_over_allow"],
        "rules": [
            {
                "name": "target_rule",
                "action": "allow",
                "scope": {"target_type": "host", "target_id": "ws-01"},
            },
            {
                "name": "asset_rule",
                "action": "deny",
                "scope": {"asset_id": "eng-workstation-pool"},
            },
            {
                "name": "catch_all_rule",
                "action": "escalate",
                "scope": {"catch_all": True},
            },
        ],
    }
    snapshot = preflight_document(doc)
    rules = snapshot.containment_policy.rules
    assert rules[0].scope.model_dump() == {
        "target_type": "host",
        "target_id": "ws-01",
    }
    assert rules[1].scope.model_dump() == {"asset_id": "eng-workstation-pool"}
    assert rules[2].scope.model_dump() == {"catch_all": True}


def test_missing_default_action_fails_preflight() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    del doc["containment_policy"]["default_action"]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "missing_default_action"


def test_invalid_default_action_fails_preflight() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_policy"]["default_action"] = "permit_all"
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_containment_policy"


def test_default_action_round_trips_in_snapshot() -> None:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    assert snapshot.containment_policy.default_action == "escalate"
    assert snapshot.containment_policy.rules == []


def test_missing_revocation_feed_section_fails() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    del doc["revocation_feed_policy"]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "missing_section"


def test_missing_consumer_clock_section_fails() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    del doc["consumer_clock_skew_policy"]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "missing_section"


def test_apply_field_defaults_does_not_mutate_caller() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    original = load_org_config_document(EXAMPLE_CONFIG)
    del doc["revocation_feed_policy"]["max_revocation_feed_propagation_delay_seconds"]
    result = apply_field_defaults(doc)
    assert "max_revocation_feed_propagation_delay_seconds" in result["revocation_feed_policy"]
    assert "max_revocation_feed_propagation_delay_seconds" not in doc["revocation_feed_policy"]
    assert original["revocation_feed_policy"]["max_revocation_feed_propagation_delay_seconds"] == 60


def test_account_auto_contain_omitted_defaults_false() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    del doc["account_auto_contain_enabled"]
    snapshot = preflight_document(doc)
    assert snapshot.account_auto_contain_enabled is False


def test_string_false_account_gate_rejected() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["account_auto_contain_enabled"] = "false"
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_boolean"


def test_account_auto_contain_true_rejected_in_v1() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["account_auto_contain_enabled"] = True
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "account_containment_prerequisite"


def test_invalid_never_contain_entry_rejected() -> None:
    doc = load_org_config_document(EXAMPLE_CONFIG)
    doc["containment_exclusions"]["never_contain"].append({"target_type": "host"})
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_target_specification"
