"""Empirical org-config sweep from normalized telemetry."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import yaml

from praetor.codification.models import (
    PROPOSED_ARTIFACT_KIND,
    UNOBSERVED_SUBNET_PLACEHOLDER,
    AdminPatternObservation,
    AssetObservation,
    PrincipalObservation,
    SweepEventCounts,
    SweepResult,
    SweepSummary,
)
from praetor.codification.report import build_sweep_report
from praetor.contracts.evidence import EvidenceFact
from praetor.correlation.security_log import (
    normalize_security_event,
    supports_security_event,
)
from praetor.correlation.sysmon import normalize_sysmon_event, supports_sysmon_event
from praetor.evidence.provenance import SYSMON_EVENT_LOG

_DEFAULT_POLICY_TEMPLATE: dict[str, Any] = {
    "containment_exclusions": {
        "never_contain": [
            {"target_type": "host", "target_id": "REPLACE-BEFORE-ACTIVATION"},
        ],
    },
    "business_context": {
        "notes": "Placeholder — replace after SOC review of sweep output.",
    },
    "containment_policy": {
        "precedence": ["deny_over_allow"],
        "rules": [
            {
                "name": "default_escalate",
                "action": "escalate",
                "scope": "global",
            },
        ],
    },
    "account_auto_contain_enabled": False,
    "directive_lifetime_policy": {"max_lifetime_seconds": 300},
    "emergency_never_contain_policy": {"max_lifetime_seconds": 172800},
    "rate_limit_policy": {
        "scopes": ["per_host", "per_subnet", "per_asset_group"],
    },
    "provider_health_circuit_breaker_policy": {
        "window_seconds": 60,
        "failure_threshold": 5,
        "success_reset_threshold": 3,
        "probe_rate_limit_per_minute": 10,
    },
    "containment_circuit_breaker_policy": {
        "window_seconds": 60,
        "failure_threshold": 5,
        "success_reset_threshold": 3,
    },
    "revocation_feed_policy": {
        "max_revocation_feed_propagation_delay_seconds": 60,
        "max_feed_export_retries": 3,
    },
    "consumer_clock_skew_policy": {"max_consumer_clock_skew_seconds": 30},
    "latency_and_queue_aging_policy": {"max_queue_age_seconds": 120},
    "provisional_alert_rate_targets": {
        "sustained_alerts_per_minute": 30,
        "burst_alerts_per_minute": 60,
    },
}


def is_proposed_org_config_artifact(document: Mapping[str, Any]) -> bool:
    """Return True when document is a sweep-generated proposed artifact."""
    meta = document.get("version_metadata")
    if not isinstance(meta, Mapping):
        return False
    return meta.get("artifact_kind") == PROPOSED_ARTIFACT_KIND


def run_org_config_sweep(
    *,
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
    org_id: str,
    config_version: str = "sweep-proposed-0.1.0",
) -> SweepResult:
    """Summarize telemetry and build a review-only proposed org-config artifact."""
    facts, event_counts = _normalize_events(sysmon_events, security_events)
    summary = _build_summary(facts, event_counts=event_counts)
    proposed_config = build_proposed_org_config(
        summary,
        org_id=org_id,
        config_version=config_version,
    )
    report = build_sweep_report(summary)
    return SweepResult(
        summary=summary,
        proposed_config=proposed_config,
        report=report,
    )


def build_proposed_org_config(
    summary: SweepSummary,
    *,
    org_id: str,
    config_version: str,
) -> dict[str, Any]:
    """Build a proposed org-config mapping marked non-activatable."""
    config: dict[str, Any] = {
        "version_metadata": {
            "org_id": org_id,
            "config_version": config_version,
            "artifact_kind": PROPOSED_ARTIFACT_KIND,
            "activation_status": "proposed_for_review_only",
        },
        "known_principals": {
            "service_accounts": [],
            "observed_principals": [
                {
                    "principal_id": item.principal_id,
                    "observation_count": item.observation_count,
                    "sources": sorted(item.sources),
                }
                for item in summary.principals
            ],
        },
        "assets_and_asset_groups": {
            "entries": [
                {
                    "asset_id": item.asset_id,
                    "observation_count": item.observation_count,
                    "subnet_membership": UNOBSERVED_SUBNET_PLACEHOLDER,
                    "description": "Observed host — subnet requires human review.",
                }
                for item in summary.assets
            ],
        },
        "normal_admin_patterns": {
            "patterns": [
                {
                    "name": item.name,
                    "description": item.description,
                    "observation_count": item.observation_count,
                }
                for item in summary.admin_patterns
            ],
        },
    }
    config.update(_DEFAULT_POLICY_TEMPLATE)
    return config


def render_proposed_org_config_yaml(proposed_config: Mapping[str, Any]) -> str:
    """Render proposed artifact as YAML for SOC review."""
    return yaml.safe_dump(
        dict(proposed_config),
        sort_keys=False,
        allow_unicode=True,
    )


def _normalize_events(
    sysmon_events: Sequence[Mapping[str, Any]],
    security_events: Sequence[Mapping[str, Any]],
) -> tuple[list[EvidenceFact], SweepEventCounts]:
    facts: list[EvidenceFact] = []
    sysmon_normalized = 0
    sysmon_skipped = 0
    for event in sysmon_events:
        if not supports_sysmon_event(event):
            sysmon_skipped += 1
            continue
        facts.append(normalize_sysmon_event(event))
        sysmon_normalized += 1

    security_normalized = 0
    security_skipped = 0
    for event in security_events:
        if not supports_security_event(event):
            security_skipped += 1
            continue
        facts.append(normalize_security_event(event))
        security_normalized += 1

    counts = SweepEventCounts(
        sysmon_events_seen=len(sysmon_events),
        sysmon_events_normalized=sysmon_normalized,
        sysmon_events_skipped=sysmon_skipped,
        security_events_seen=len(security_events),
        security_events_normalized=security_normalized,
        security_events_skipped=security_skipped,
    )
    return facts, counts


def _build_summary(
    facts: Sequence[EvidenceFact],
    *,
    event_counts: SweepEventCounts,
) -> SweepSummary:
    principal_counter: Counter[str] = Counter()
    principal_sources: dict[str, set[str]] = {}
    asset_counter: Counter[str] = Counter()
    admin_counter: Counter[tuple[str, str, str | None, str | None]] = Counter()

    timestamps: list[datetime] = []

    for fact in facts:
        timestamps.append(fact.timestamp)
        host_id = str(fact.normalized_fields.get("host_id") or "").lower()
        if host_id:
            asset_counter[host_id] += 1

        if fact.provenance_path == SYSMON_EVENT_LOG:
            user = str(fact.normalized_fields.get("user") or "")
            if user:
                key = user.lower()
                principal_counter[key] += 1
                principal_sources.setdefault(key, set()).add("sysmon_user")

            parent_name = str(fact.normalized_fields.get("parent_process_name") or "")
            process_name = str(fact.normalized_fields.get("process_name") or "")
            if parent_name and process_name:
                pattern_key = f"{parent_name} -> {process_name}"
                admin_key = (pattern_key, pattern_key, host_id or None, user or None)
                admin_counter[admin_key] += 1
            continue

        account_name = str(fact.normalized_fields.get("account_name") or "")
        domain = str(fact.normalized_fields.get("domain") or "")
        if account_name:
            principal_id = (
                f"{domain}\\{account_name}" if domain else account_name
            ).lower()
            principal_counter[principal_id] += 1
            principal_sources.setdefault(principal_id, set()).add("security_account")

    principals = tuple(
        PrincipalObservation(
            principal_id=principal_id,
            observation_count=count,
            sources=frozenset(principal_sources.get(principal_id, set())),
        )
        for principal_id, count in sorted(principal_counter.items())
    )
    assets = tuple(
        AssetObservation(asset_id=asset_id, observation_count=count)
        for asset_id, count in sorted(asset_counter.items())
    )
    admin_patterns = tuple(
        AdminPatternObservation(
            name=_admin_pattern_name(pattern_key),
            description=_admin_pattern_description(
                pattern_key,
                host_id=host_id,
                user=user,
                count=count,
            ),
            observation_count=count,
            host_id=host_id,
            user=user,
        )
        for (_, pattern_key, host_id, user), count in sorted(
            admin_counter.items(),
            key=lambda item: (-item[1], item[0][1], item[0][2] or "", item[0][3] or ""),
        )
    )

    earliest = min(timestamps) if timestamps else None
    latest = max(timestamps) if timestamps else None

    return SweepSummary(
        principals=principals,
        assets=assets,
        admin_patterns=admin_patterns,
        event_counts=event_counts,
        earliest_timestamp=earliest,
        latest_timestamp=latest,
    )


def _admin_pattern_name(pattern_key: str) -> str:
    slug = (
        pattern_key.lower()
        .replace(" -> ", "_to_")
        .replace(".exe", "")
        .replace("\\", "_")
        .replace(" ", "_")
    )
    return f"sweep_observed_{slug}"


def _admin_pattern_description(
    pattern_key: str,
    *,
    host_id: str | None,
    user: str | None,
    count: int,
) -> str:
    parts = [f"Observed {count} time(s): {pattern_key}"]
    if user:
        parts.append(f"user={user}")
    if host_id:
        parts.append(f"host={host_id}")
    parts.append("Heuristic only — requires SOC validation before treating as benign.")
    return "; ".join(parts)


__all__ = [
    "PROPOSED_ARTIFACT_KIND",
    "AdminPatternObservation",
    "AssetObservation",
    "PrincipalObservation",
    "SweepEventCounts",
    "SweepResult",
    "SweepSummary",
    "UNOBSERVED_SUBNET_PLACEHOLDER",
    "build_proposed_org_config",
    "is_proposed_org_config_artifact",
    "render_proposed_org_config_yaml",
    "run_org_config_sweep",
]
