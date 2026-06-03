"""Org config activation preflight (docs/spec.md § Org Config)."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from praetor.config.constants import (
    DEFAULT_CLOCK_SKEW_SECONDS,
    DEFAULT_FEED_PROPAGATION_SECONDS,
    DIRECTIVE_MAX_SECONDS,
    EMERGENCY_MAX_SECONDS,
    HARD_CONFIG_CHARACTER_BUDGET,
    RATE_LIMIT_SCOPES,
    REQUIRED_TOP_LEVEL_SECTIONS,
)
from praetor.config.errors import PreflightError
from praetor.config.live import (
    permanent_never_contain_entries,
    validate_never_contain_entries,
)
from praetor.config.loader import deep_copy_document
from praetor.config.snapshot import (
    build_org_config_snapshot,
    reject_unknown_top_level_keys,
    verbatim_character_count,
)
from praetor.contracts.org_config import OrgConfigSnapshot


def _require_bool(value: Any, *, field: str) -> bool:
    if type(value) is not bool:
        raise PreflightError("invalid_boolean", f"{field} must be a boolean")
    return value


def _require_positive_int(
    value: Any,
    *,
    field: str,
    maximum: int | None = None,
    code: str = "invalid_section",
) -> int:
    if type(value) is not int:
        raise PreflightError(code, f"{field} must be an integer")
    if value <= 0:
        raise PreflightError(code, f"{field} must be positive")
    if maximum is not None and value > maximum:
        raise PreflightError(code, f"{field} exceeds maximum {maximum}")
    return value


def apply_field_defaults(document: dict[str, Any]) -> dict[str, Any]:
    doc = deep_copy_document(document)
    if "account_auto_contain_enabled" not in doc:
        doc["account_auto_contain_enabled"] = False
    else:
        doc["account_auto_contain_enabled"] = _require_bool(
            doc["account_auto_contain_enabled"],
            field="account_auto_contain_enabled",
        )
    if doc["account_auto_contain_enabled"]:
        raise PreflightError(
            "account_containment_prerequisite",
            "account_auto_contain_enabled is not permitted in v1 org config",
        )

    feed = doc["revocation_feed_policy"]
    if not isinstance(feed, dict):
        raise PreflightError("invalid_section", "revocation_feed_policy must be a mapping")
    if "max_revocation_feed_propagation_delay_seconds" not in feed:
        feed["max_revocation_feed_propagation_delay_seconds"] = DEFAULT_FEED_PROPAGATION_SECONDS
    else:
        feed["max_revocation_feed_propagation_delay_seconds"] = _require_positive_int(
            feed["max_revocation_feed_propagation_delay_seconds"],
            field="revocation_feed_policy.max_revocation_feed_propagation_delay_seconds",
            code="invalid_feed_policy",
        )
    if "max_feed_export_retries" not in feed:
        raise PreflightError(
            "invalid_feed_policy",
            "revocation_feed_policy.max_feed_export_retries required",
        )
    feed["max_feed_export_retries"] = _require_positive_int(
        feed["max_feed_export_retries"],
        field="revocation_feed_policy.max_feed_export_retries",
        code="invalid_feed_policy",
    )

    clock = doc["consumer_clock_skew_policy"]
    if not isinstance(clock, dict):
        raise PreflightError("invalid_section", "consumer_clock_skew_policy must be a mapping")
    if "max_consumer_clock_skew_seconds" not in clock:
        clock["max_consumer_clock_skew_seconds"] = DEFAULT_CLOCK_SKEW_SECONDS
    else:
        clock["max_consumer_clock_skew_seconds"] = _require_positive_int(
            clock["max_consumer_clock_skew_seconds"],
            field="consumer_clock_skew_policy.max_consumer_clock_skew_seconds",
            code="invalid_section",
        )

    return doc


def run_preflight(document: dict[str, Any], *, verbatim_text: str) -> OrgConfigSnapshot:
    reject_unknown_top_level_keys(document)

    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section not in document:
            raise PreflightError("missing_section", f"missing required section: {section}")

    if verbatim_character_count(verbatim_text) > HARD_CONFIG_CHARACTER_BUDGET:
        raise PreflightError("config_over_budget", "org config exceeds hard character budget")

    doc = apply_field_defaults(document)

    never_contain = permanent_never_contain_entries(doc["containment_exclusions"])
    validate_never_contain_entries(never_contain)

    _validate_rate_limit_scopes(doc["rate_limit_policy"])
    _validate_containment_policy_conflicts(doc["containment_policy"])
    _validate_policy_integer_fields(doc)
    _validate_provisional_targets(doc["provisional_alert_rate_targets"])

    try:
        snapshot = build_org_config_snapshot(doc)
    except PreflightError:
        raise
    except ValidationError as exc:
        raise PreflightError("invalid_snapshot", str(exc)) from exc

    _validate_policy_caps(snapshot)
    return snapshot


def _validate_policy_integer_fields(doc: dict[str, Any]) -> None:
    """Reject quoted/coerced numerics before Pydantic snapshot build."""
    directive = doc["directive_lifetime_policy"]
    if not isinstance(directive, dict):
        raise PreflightError("invalid_section", "directive_lifetime_policy must be a mapping")
    _require_positive_int(
        directive.get("max_lifetime_seconds"),
        field="directive_lifetime_policy.max_lifetime_seconds",
        code="invalid_directive_lifetime",
    )

    emergency = doc["emergency_never_contain_policy"]
    if not isinstance(emergency, dict):
        raise PreflightError("invalid_section", "emergency_never_contain_policy must be a mapping")
    _require_positive_int(
        emergency.get("max_lifetime_seconds"),
        field="emergency_never_contain_policy.max_lifetime_seconds",
        code="invalid_emergency_lifetime",
    )

    _validate_circuit_breaker_integers(
        doc["provider_health_circuit_breaker_policy"],
        section_name="provider_health_circuit_breaker_policy",
        extra_fields=("probe_rate_limit_per_minute",),
    )
    _validate_circuit_breaker_integers(
        doc["containment_circuit_breaker_policy"],
        section_name="containment_circuit_breaker_policy",
    )

    latency = doc["latency_and_queue_aging_policy"]
    if not isinstance(latency, dict):
        raise PreflightError("invalid_section", "latency_and_queue_aging_policy must be a mapping")
    _require_positive_int(
        latency.get("max_queue_age_seconds"),
        field="latency_and_queue_aging_policy.max_queue_age_seconds",
        code="invalid_section",
    )


def _validate_circuit_breaker_integers(
    section: Any,
    *,
    section_name: str,
    extra_fields: tuple[str, ...] = (),
) -> None:
    if not isinstance(section, dict):
        raise PreflightError("invalid_section", f"{section_name} must be a mapping")
    for field in ("window_seconds", "failure_threshold", "success_reset_threshold", *extra_fields):
        if field not in section:
            raise PreflightError("invalid_section", f"{section_name}.{field} required")
        _require_positive_int(
            section[field],
            field=f"{section_name}.{field}",
            code="invalid_section",
        )


def _validate_provisional_targets(section: Any) -> None:
    if not isinstance(section, dict):
        raise PreflightError("missing_provisional_targets", "provisional section must be a mapping")
    for key in ("sustained_alerts_per_minute", "burst_alerts_per_minute"):
        if key not in section:
            raise PreflightError("missing_provisional_targets", f"missing {key}")
        _require_positive_int(section[key], field=key, code="missing_provisional_targets")


def _validate_rate_limit_scopes(policy: Any) -> None:
    if not isinstance(policy, dict):
        raise PreflightError("invalid_rate_limits", "rate_limit_policy must be a mapping")
    scopes = policy.get("scopes")
    if not isinstance(scopes, list):
        raise PreflightError("invalid_rate_limits", "rate_limit_policy.scopes must be a list")
    for scope in scopes:
        if scope not in RATE_LIMIT_SCOPES:
            raise PreflightError("invalid_rate_limits", f"unknown rate_limit scope: {scope!r}")
    missing = RATE_LIMIT_SCOPES - set(scopes)
    if missing:
        raise PreflightError(
            "invalid_rate_limits",
            f"rate_limit_policy missing scopes: {sorted(missing)}",
        )


def _validate_containment_policy_conflicts(policy: Any) -> None:
    if not isinstance(policy, dict):
        raise PreflightError("invalid_containment_policy", "containment_policy must be a mapping")
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        raise PreflightError("invalid_containment_policy", "containment_policy.rules required")
    precedence = policy.get("precedence")
    if precedence is not None:
        if not isinstance(precedence, list) or not precedence:
            raise PreflightError(
                "invalid_containment_policy",
                "containment_policy.precedence must be a non-empty list when present",
            )
    actions: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise PreflightError("invalid_containment_policy", "each rule must be a mapping")
        action = rule.get("action")
        if action is not None:
            if not isinstance(action, str):
                raise PreflightError("invalid_containment_policy", "rule action must be a string")
            actions.add(action)
    if len(actions) > 1 and not precedence:
        raise PreflightError(
            "containment_policy_conflict",
            "containment policy conflicts without precedence",
        )


def _validate_policy_caps(snapshot: OrgConfigSnapshot) -> None:
    if snapshot.directive_lifetime_policy.max_lifetime_seconds > DIRECTIVE_MAX_SECONDS:
        raise PreflightError("invalid_directive_lifetime", "directive max exceeds hard cap")
    if snapshot.emergency_never_contain_policy.max_lifetime_seconds > EMERGENCY_MAX_SECONDS:
        raise PreflightError("invalid_emergency_lifetime", "emergency max exceeds hard cap")
    propagation = snapshot.revocation_feed_policy.max_revocation_feed_propagation_delay_seconds
    directive_max = snapshot.directive_lifetime_policy.max_lifetime_seconds
    if propagation >= directive_max:
        raise PreflightError(
            "invalid_feed_propagation",
            "feed propagation delay must be below directive max lifetime",
        )
