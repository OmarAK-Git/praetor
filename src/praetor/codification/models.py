"""Shared types and sentinel constants for org-config codification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

PROPOSED_ARTIFACT_KIND = "proposed_org_config"
UNOBSERVED_SUBNET_PLACEHOLDER = "UNOBSERVED-REQUIRES-HUMAN-REVIEW"
REPLACE_BEFORE_ACTIVATION_NEVER_CONTAIN_TARGET = "REPLACE-BEFORE-ACTIVATION"
ZERO_EVIDENCE_ACTIVATION_STATUS = "unusable_zero_evidence"

SWEEP_PLACEHOLDER_SENTINELS: frozenset[str] = frozenset(
    {
        UNOBSERVED_SUBNET_PLACEHOLDER,
        REPLACE_BEFORE_ACTIVATION_NEVER_CONTAIN_TARGET,
    }
)


@dataclass(frozen=True)
class PrincipalObservation:
    principal_id: str
    observation_count: int
    sources: frozenset[str]
    ambiguous_observation_count: int


@dataclass(frozen=True)
class AssetObservation:
    asset_id: str
    observation_count: int


@dataclass(frozen=True)
class AdminPatternObservation:
    name: str
    description: str
    observation_count: int
    host_id: str | None
    user: str | None
    pattern_key: str


@dataclass(frozen=True)
class SweepEventCounts:
    sysmon_events_seen: int
    sysmon_events_normalized: int
    sysmon_events_skipped: int
    security_events_seen: int
    security_events_normalized: int
    security_events_skipped: int

    @property
    def normalized_total(self) -> int:
        return self.sysmon_events_normalized + self.security_events_normalized


@dataclass(frozen=True)
class SweepSummary:
    principals: tuple[PrincipalObservation, ...]
    assets: tuple[AssetObservation, ...]
    admin_patterns: tuple[AdminPatternObservation, ...]
    event_counts: SweepEventCounts
    earliest_timestamp: datetime | None
    latest_timestamp: datetime | None

    @property
    def has_normalized_evidence(self) -> bool:
        return self.event_counts.normalized_total > 0


@dataclass(frozen=True)
class CoverageLimit:
    code: str
    description: str


@dataclass(frozen=True)
class AbsenceOfEvidenceRisk:
    code: str
    description: str


@dataclass(frozen=True)
class SweepReport:
    coverage_limits: tuple[CoverageLimit, ...]
    absence_of_evidence_risks: tuple[AbsenceOfEvidenceRisk, ...]
    summary_text: str


@dataclass(frozen=True)
class SweepResult:
    summary: SweepSummary
    proposed_config: dict[str, Any]
    report: SweepReport
