"""Detect unreplaced sweep placeholder sentinel values in org-config documents."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from praetor.codification.models import (
    PROPOSED_ARTIFACT_KIND,
    PROPOSED_STATUTE_ARTIFACT_KIND,
    REPLACE_BEFORE_ACTIVATION_NEVER_CONTAIN_TARGET,
    SWEEP_PLACEHOLDER_SENTINELS,
    UNOBSERVED_SUBNET_PLACEHOLDER,
)

REVIEW_ONLY_PROPOSED_ARTIFACT_KINDS: frozenset[str] = frozenset(
    {
        PROPOSED_ARTIFACT_KIND,
        PROPOSED_STATUTE_ARTIFACT_KIND,
    }
)


def is_proposed_org_config_artifact(document: Mapping[str, Any]) -> bool:
    """Return True when document is a review-only proposed artifact."""
    meta = document.get("version_metadata")
    if not isinstance(meta, Mapping):
        return False
    return meta.get("artifact_kind") in REVIEW_ONLY_PROPOSED_ARTIFACT_KINDS


def is_proposed_statute_artifact(document: Mapping[str, Any]) -> bool:
    """Return True when document is an annotation-derived proposed statute artifact."""
    meta = document.get("version_metadata")
    if not isinstance(meta, Mapping):
        return False
    return meta.get("artifact_kind") == PROPOSED_STATUTE_ARTIFACT_KIND


def collect_sweep_placeholder_violations(document: Mapping[str, Any]) -> list[str]:
    """Return dotted paths where sweep sentinel placeholder values remain."""
    violations: list[str] = []

    assets = document.get("assets_and_asset_groups")
    if isinstance(assets, Mapping):
        entries = assets.get("entries")
        if isinstance(entries, list):
            for index, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    continue
                subnet = entry.get("subnet_membership")
                if subnet in SWEEP_PLACEHOLDER_SENTINELS:
                    violations.append(
                        f"assets_and_asset_groups.entries[{index}].subnet_membership"
                    )

    exclusions = document.get("containment_exclusions")
    if isinstance(exclusions, Mapping):
        never_contain = exclusions.get("never_contain")
        if isinstance(never_contain, list):
            for index, entry in enumerate(never_contain):
                if not isinstance(entry, Mapping):
                    continue
                target_id = entry.get("target_id")
                if target_id in SWEEP_PLACEHOLDER_SENTINELS:
                    violations.append(
                        f"containment_exclusions.never_contain[{index}].target_id"
                    )

    return violations


def document_has_unreplaced_sweep_placeholders(document: Mapping[str, Any]) -> bool:
    return bool(collect_sweep_placeholder_violations(document))


__all__ = [
    "REPLACE_BEFORE_ACTIVATION_NEVER_CONTAIN_TARGET",
    "REVIEW_ONLY_PROPOSED_ARTIFACT_KINDS",
    "UNOBSERVED_SUBNET_PLACEHOLDER",
    "collect_sweep_placeholder_violations",
    "document_has_unreplaced_sweep_placeholders",
    "is_proposed_org_config_artifact",
    "is_proposed_statute_artifact",
]
