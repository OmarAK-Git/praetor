"""Typed org-config section shapes; extra fields allowed where spec is open-ended."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, StrictInt

from praetor.contracts._base import ContractModel

TargetTypeLiteral = Literal["host", "account"]


class NeverContainEntry(ContractModel):
    target_type: TargetTypeLiteral
    target_id: str = Field(..., min_length=1)


class ContainmentExclusions(ContractModel):
    never_contain: list[NeverContainEntry] = Field(..., min_length=1)


class AssetEntry(ContractModel):
    model_config = ConfigDict(extra="allow")

    asset_id: str = Field(..., min_length=1)
    subnet_membership: str = Field(..., min_length=1)


class AssetsAndAssetGroups(ContractModel):
    model_config = ConfigDict(extra="allow")

    entries: list[AssetEntry] = Field(..., min_length=1)


class ContainmentRule(ContractModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)


class ContainmentPolicy(ContractModel):
    model_config = ConfigDict(extra="allow")

    rules: list[ContainmentRule] = Field(..., min_length=1)
    precedence: list[str] | None = None


class DirectiveLifetimePolicy(ContractModel):
    max_lifetime_seconds: StrictInt = Field(..., gt=0)


class EmergencyNeverContainPolicy(ContractModel):
    max_lifetime_seconds: StrictInt = Field(..., gt=0)


class RateLimitPolicy(ContractModel):
    scopes: list[str] = Field(..., min_length=1)


class CircuitBreakerPolicy(ContractModel):
    window_seconds: StrictInt = Field(..., gt=0)
    failure_threshold: StrictInt = Field(..., gt=0)
    success_reset_threshold: StrictInt = Field(..., gt=0)


class ProviderHealthCircuitBreakerPolicy(CircuitBreakerPolicy):
    probe_rate_limit_per_minute: StrictInt = Field(..., gt=0)


class RevocationFeedPolicy(ContractModel):
    max_revocation_feed_propagation_delay_seconds: StrictInt = Field(..., gt=0)
    max_feed_export_retries: StrictInt = Field(..., gt=0)


class ConsumerClockSkewPolicy(ContractModel):
    max_consumer_clock_skew_seconds: StrictInt = Field(..., gt=0)


class ProvisionalAlertRateTargets(ContractModel):
    sustained_alerts_per_minute: StrictInt = Field(..., gt=0)
    burst_alerts_per_minute: StrictInt = Field(..., gt=0)


class VersionMetadata(ContractModel):
    model_config = ConfigDict(extra="allow")

    org_id: str = Field(..., min_length=1)
    config_version: str = Field(..., min_length=1)


class KnownPrincipals(ContractModel):
    model_config = ConfigDict(extra="allow")


class NormalAdminPatterns(ContractModel):
    model_config = ConfigDict(extra="allow")


class BusinessContext(ContractModel):
    model_config = ConfigDict(extra="allow")


class LatencyAndQueueAgingPolicy(ContractModel):
    max_queue_age_seconds: StrictInt = Field(..., gt=0)
