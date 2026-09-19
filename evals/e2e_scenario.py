"""E2E kernel scenario YAML contract loader (spec §4)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from evals.e2e_kernel import E2E_SCENARIOS_DIR
from evals.scorecard import Arm, ProviderKind, Realm

THEATER_DETECTOR_NAMES: frozenset[str] = frozenset(
    {
        "label_leak",
        "stipulated_capability",
        "unearned_demo_claim",
        "path_b_in_src",
        "post_hoc_protocol",
        "gate_scored_as_judgment",
    }
)
SCHEMA_PATH = (
    Path(__file__).resolve().parent / "schemas" / "e2e_scenario_schema.json"
)


@dataclass(frozen=True)
class E2EArmConfig:
    expected: Mapping[str, Any]
    provider: ProviderKind


@dataclass(frozen=True)
class E2EScenarioDocument:
    schema_version: str
    scenario_id: str
    realm: Realm
    description: str
    runner: Literal["e2e_kernel"]
    setup: Mapping[str, Any]
    arms: Mapping[Arm, E2EArmConfig]
    scorecard_pins: tuple[str, ...]
    theater_detector: str
    source_path: Path


def _load_schema() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _validate_object(
    data: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    defs: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for key in required:
        if key not in data:
            errors.append(f"missing required field: {key}")
    if schema.get("additionalProperties") is False:
        extra = set(data.keys()) - set(properties)
        if extra:
            errors.append(f"unexpected fields: {sorted(extra)}")
    for key, spec in properties.items():
        if key not in data or not isinstance(spec, dict):
            continue
        if "$ref" in spec:
            ref_name = str(spec["$ref"]).rsplit("/", 1)[-1]
            errors.extend(_validate_object(data[key], defs[ref_name], defs=defs))
            continue
        if spec.get("const") is not None and data[key] != spec["const"]:
            errors.append(f"{key}: expected {spec['const']!r}, got {data[key]!r}")
        if spec.get("enum") and data[key] not in spec["enum"]:
            errors.append(f"{key}: {data[key]!r} not in enum {spec['enum']}")
        if spec.get("type") == "object" and isinstance(data[key], Mapping):
            errors.extend(_validate_object(data[key], spec, defs=defs))
        if spec.get("type") == "array" and key == "scorecard_pins":
            pins = data[key]
            if not isinstance(pins, list) or not pins:
                errors.append("scorecard_pins must be a non-empty list")
    return errors


def load_e2e_scenario(path: Path) -> E2EScenarioDocument:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: scenario root must be a mapping")
    schema = _load_schema()
    defs = schema.get("$defs", {})
    errors = _validate_object(raw, schema, defs=defs)
    arms_raw = raw.get("arms", {})
    if isinstance(arms_raw, Mapping):
        for arm_name, arm_body in arms_raw.items():
            if isinstance(arm_body, Mapping):
                errors.extend(
                    _validate_object(arm_body, defs["arm"], defs=defs)
                )
            else:
                errors.append(f"arms.{arm_name} must be a mapping")
    theater = str(raw.get("theater_detector", ""))
    if theater and theater not in THEATER_DETECTOR_NAMES:
        errors.append(
            f"theater_detector: {theater!r} not in {sorted(THEATER_DETECTOR_NAMES)}"
        )
    if errors:
        raise ValueError(f"{path.name}: schema validation failed: {'; '.join(errors)}")
    scenario_id = str(raw["scenario_id"])
    if path.stem != scenario_id:
        raise ValueError(
            f"{path.name}: filename stem must match scenario_id {scenario_id!r}"
        )
    arms = {
        cast(Arm, name): E2EArmConfig(
            expected=body["expected"],
            provider=cast(ProviderKind, body["provider"]),
        )
        for name, body in arms_raw.items()
    }
    return E2EScenarioDocument(
        schema_version=str(raw["schema_version"]),
        scenario_id=scenario_id,
        realm=cast(Realm, raw["realm"]),
        description=str(raw["description"]),
        runner="e2e_kernel",
        setup=raw["setup"],
        arms=arms,
        scorecard_pins=tuple(str(pin) for pin in raw["scorecard_pins"]),
        theater_detector=theater,
        source_path=path,
    )


def list_e2e_scenarios(scenarios_dir: Path | None = None) -> list[E2EScenarioDocument]:
    directory = scenarios_dir or E2E_SCENARIOS_DIR
    return [load_e2e_scenario(path) for path in sorted(directory.glob("*.yaml"))]
