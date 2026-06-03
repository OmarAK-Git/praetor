"""Bound org-config snapshot contract."""

from __future__ import annotations

from pydantic import Field

from praetor.contracts._base import SCHEMA_VERSION_V1, ContractModel, SchemaVersionV1
from praetor.contracts.org_config_sections import (
    AssetsAndAssetGroups,
    BusinessContext,
    ConsumerClockSkewPolicy,
    ContainmentExclusions,
    ContainmentPolicy,
    DirectiveLifetimePolicy,
    EmergencyNeverContainPolicy,
    KnownPrincipals,
    LatencyAndQueueAgingPolicy,
    NormalAdminPatterns,
    ProviderHealthCircuitBreakerPolicy,
    ProvisionalAlertRateTargets,
    RateLimitPolicy,
    RevocationFeedPolicy,
    VersionMetadata,
)
from praetor.contracts.org_config_sections import (
    CircuitBreakerPolicy as ContainmentCircuitBreakerPolicy,
)


class OrgConfigSnapshot(ContractModel):
    """Bound org-config snapshot at activation."""

    schema_version: SchemaVersionV1 = SCHEMA_VERSION_V1
    snapshot_hash: str = Field(
        ...,
        description="Canonical hash of binding body per docs/contracts.md §3a.",
    )
    version_metadata: VersionMetadata
    known_principals: KnownPrincipals
    assets_and_asset_groups: AssetsAndAssetGroups
    normal_admin_patterns: NormalAdminPatterns
    containment_exclusions: ContainmentExclusions
    business_context: BusinessContext
    containment_policy: ContainmentPolicy
    account_auto_contain_enabled: bool = False
    directive_lifetime_policy: DirectiveLifetimePolicy
    emergency_never_contain_policy: EmergencyNeverContainPolicy
    rate_limit_policy: RateLimitPolicy
    provider_health_circuit_breaker_policy: ProviderHealthCircuitBreakerPolicy
    containment_circuit_breaker_policy: ContainmentCircuitBreakerPolicy
    revocation_feed_policy: RevocationFeedPolicy
    consumer_clock_skew_policy: ConsumerClockSkewPolicy
    latency_and_queue_aging_policy: LatencyAndQueueAgingPolicy
    provisional_alert_rate_targets: ProvisionalAlertRateTargets
