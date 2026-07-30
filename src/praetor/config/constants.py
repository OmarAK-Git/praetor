"""Org config constants (docs/contracts.md §3a, §11)."""

from __future__ import annotations

HARD_CONFIG_CHARACTER_BUDGET = 400_000

DIRECTIVE_MAX_SECONDS = 300
EMERGENCY_MAX_SECONDS = 48 * 3600
DEFAULT_FEED_PROPAGATION_SECONDS = 60
DEFAULT_CLOCK_SKEW_SECONDS = 30

# Operator visibility only — not a rotation trigger. Feed rotation remains a
# deferred v1 non-goal (docs/operator_runbook.md "no rotation machinery").
# Provisional threshold pending owner-set org-config value.
DEFAULT_FEED_FILE_SIZE_WARNING_BYTES = 500_000_000

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "version_metadata",
    "known_principals",
    "assets_and_asset_groups",
    "normal_admin_patterns",
    "containment_exclusions",
    "business_context",
    "containment_policy",
    "directive_lifetime_policy",
    "emergency_never_contain_policy",
    "rate_limit_policy",
    "provider_health_circuit_breaker_policy",
    "containment_circuit_breaker_policy",
    "revocation_feed_policy",
    "consumer_clock_skew_policy",
    "latency_and_queue_aging_policy",
    "provisional_alert_rate_targets",
)

OPTIONAL_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"account_auto_contain_enabled"})

ALLOWED_TOP_LEVEL_KEYS: frozenset[str] = (
    frozenset(REQUIRED_TOP_LEVEL_SECTIONS) | OPTIONAL_TOP_LEVEL_KEYS
)

RATE_LIMIT_SCOPES = frozenset({"per_host", "per_subnet", "per_asset_group"})
