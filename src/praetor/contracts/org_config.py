"""Org config snapshot (minimal section keys; nested shapes deferred to Task 9)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1


class OrgConfigSnapshot(ContractModel):
    """Bound org-config snapshot; section bodies are opaque until loader task defines shapes."""

    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    snapshot_hash: str = Field(..., description="Canonical hash of snapshot content (computed Task 3).")
    version_metadata: dict[str, Any]
    known_principals: dict[str, Any]
    assets_and_asset_groups: dict[str, Any]
    normal_admin_patterns: dict[str, Any]
    containment_exclusions: dict[str, Any]
    business_context: dict[str, Any]
    containment_policy: dict[str, Any]
    account_auto_contain_enabled: bool = False
    directive_lifetime_policy: dict[str, Any]
    emergency_never_contain_policy: dict[str, Any]
    rate_limit_policy: dict[str, Any]
    provider_health_circuit_breaker_policy: dict[str, Any]
    containment_circuit_breaker_policy: dict[str, Any]
    revocation_feed_policy: dict[str, Any]
    consumer_clock_skew_policy: dict[str, Any]
    latency_and_queue_aging_policy: dict[str, Any]
    provisional_alert_rate_targets: dict[str, Any]
