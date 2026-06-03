"""Load human-authored org config from YAML."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from praetor.config.errors import ConfigLoadError


@dataclass(frozen=True)
class LoadedOrgConfig:
    """Parsed document plus verbatim source text for judgment render."""

    document: dict[str, Any]
    verbatim_text: str
    source_path: Path


class UniqueKeyLoader(yaml.SafeLoader):  # type: ignore[misc]
    """Reject duplicate mapping keys and non-string keys."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConfigLoadError(f"org config key must be a string, got {type(key).__name__}")
        if key in mapping:
            raise ConfigLoadError(f"duplicate org config key: {key!r}")
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_org_config_source(path: Path) -> LoadedOrgConfig:
    """Load org config: structured dict + verbatim UTF-8 source (duplicate keys rejected)."""
    try:
        verbatim_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigLoadError(f"cannot read config: {path}") from exc
    try:
        data = yaml.load(verbatim_text, Loader=UniqueKeyLoader)
    except ConfigLoadError:
        raise
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"invalid YAML in {path}") from exc
    except Exception as exc:
        raise ConfigLoadError(f"invalid YAML in {path}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError("org config root must be a mapping")
    return LoadedOrgConfig(document=data, verbatim_text=verbatim_text, source_path=path)


def load_org_config_document(path: Path) -> dict[str, Any]:
    """Load structured org config document only."""
    return load_org_config_source(path).document


def deep_copy_document(document: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(document)
