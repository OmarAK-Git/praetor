"""Read-only progressive authorization reporting (V2-032)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY = True


class _AnnotationBucket(TypedDict):
    annotations_total: int
    disposition_correct_total: int
    disposition_incorrect_total: int
    corrected_disposition_counts: dict[str, int]


@dataclass(frozen=True)
class PolicyGateDimensionMetrics:
    target_type: str
    asset_class: str
    policy_gate_evaluations_total: int
    policy_gate_override_total: int

    @property
    def policy_gate_override_rate(self) -> float | None:
        if self.policy_gate_evaluations_total == 0:
            return None
        return self.policy_gate_override_total / self.policy_gate_evaluations_total


@dataclass(frozen=True)
class AnnotationOutcomeMetrics:
    target_type: str
    asset_class: str
    annotations_total: int
    disposition_correct_total: int
    disposition_incorrect_total: int
    corrected_disposition_counts: dict[str, int]

    @property
    def disposition_correct_rate(self) -> float | None:
        if self.annotations_total == 0:
            return None
        return self.disposition_correct_total / self.annotations_total


@dataclass(frozen=True)
class ProgressiveAuthorizationReport:
    """Read-only decision-support view; never mutates org config."""

    window_start: datetime
    window_end: datetime
    policy_gate_by_dimension: tuple[PolicyGateDimensionMetrics, ...]
    annotation_outcomes_by_dimension: tuple[AnnotationOutcomeMetrics, ...]
    read_only: bool = PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY


def _normalize_window_bound(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def build_progressive_authorization_report(
    conn: sqlite3.Connection,
    *,
    window_start: datetime,
    window_end: datetime,
) -> ProgressiveAuthorizationReport:
    """Aggregate PolicyGate override rate and annotation outcomes by dimension.

    Query-only: performs SELECT aggregation over persisted evaluation rows and
    analyst annotations. Does not write configuration or evaluation data.
    """
    start_key = _normalize_window_bound(window_start)
    end_key = _normalize_window_bound(window_end)

    gate_rows = conn.execute(
        """
        SELECT
            target_type,
            asset_class,
            COUNT(*) AS evaluations_total,
            SUM(overridden) AS override_total
        FROM policy_gate_evaluations
        WHERE evaluated_at >= ?
          AND evaluated_at < ?
        GROUP BY target_type, asset_class
        ORDER BY target_type, asset_class
        """,
        (start_key, end_key),
    ).fetchall()

    policy_gate_by_dimension = tuple(
        PolicyGateDimensionMetrics(
            target_type=str(row["target_type"]),
            asset_class=str(row["asset_class"]),
            policy_gate_evaluations_total=int(row["evaluations_total"]),
            policy_gate_override_total=int(row["override_total"]),
        )
        for row in gate_rows
    )

    annotation_rows = conn.execute(
        """
        SELECT
            pge.target_type,
            pge.asset_class,
            COUNT(a.annotation_id) AS annotations_total,
            SUM(
                CASE
                    WHEN json_extract(a.annotation_json, '$.disposition_correct') = 1
                         OR json_extract(
                             a.annotation_json, '$.disposition_correct'
                         ) = 'true'
                    THEN 1
                    ELSE 0
                END
            ) AS disposition_correct_total,
            SUM(
                CASE
                    WHEN json_extract(a.annotation_json, '$.disposition_correct') = 0
                         OR json_extract(
                             a.annotation_json, '$.disposition_correct'
                         ) = 'false'
                    THEN 1
                    ELSE 0
                END
            ) AS disposition_incorrect_total,
            json_extract(
                a.annotation_json, '$.corrected_disposition'
            ) AS corrected_disposition
        FROM analyst_annotations a
        INNER JOIN policy_gate_evaluations pge
            ON pge.decision_id = a.decision_id
        WHERE json_extract(a.annotation_json, '$.timestamp') >= ?
          AND json_extract(a.annotation_json, '$.timestamp') < ?
        GROUP BY pge.target_type, pge.asset_class, corrected_disposition
        ORDER BY pge.target_type, pge.asset_class, corrected_disposition
        """,
        (start_key, end_key),
    ).fetchall()

    annotation_buckets: dict[tuple[str, str], _AnnotationBucket] = {}
    for row in annotation_rows:
        key = (str(row["target_type"]), str(row["asset_class"]))
        bucket = annotation_buckets.setdefault(
            key,
            {
                "annotations_total": 0,
                "disposition_correct_total": 0,
                "disposition_incorrect_total": 0,
                "corrected_disposition_counts": {},
            },
        )
        count = int(row["annotations_total"])
        bucket["annotations_total"] += count
        bucket["disposition_correct_total"] += int(row["disposition_correct_total"])
        bucket["disposition_incorrect_total"] += int(row["disposition_incorrect_total"])
        corrected = row["corrected_disposition"]
        if corrected is not None:
            corrected_key = str(corrected)
            counts = bucket["corrected_disposition_counts"]
            counts[corrected_key] = counts.get(corrected_key, 0) + count

    annotation_outcomes_by_dimension = tuple(
        AnnotationOutcomeMetrics(
            target_type=target_type,
            asset_class=asset_class,
            annotations_total=bucket["annotations_total"],
            disposition_correct_total=bucket["disposition_correct_total"],
            disposition_incorrect_total=bucket["disposition_incorrect_total"],
            corrected_disposition_counts=dict(bucket["corrected_disposition_counts"]),
        )
        for (target_type, asset_class), bucket in sorted(annotation_buckets.items())
    )

    return ProgressiveAuthorizationReport(
        window_start=window_start,
        window_end=window_end,
        policy_gate_by_dimension=policy_gate_by_dimension,
        annotation_outcomes_by_dimension=annotation_outcomes_by_dimension,
    )
