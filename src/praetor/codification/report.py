"""Coverage and risk reporting for org-config sweeps."""

from __future__ import annotations

from praetor.codification.models import (
    UNOBSERVED_SUBNET_PLACEHOLDER,
    AbsenceOfEvidenceRisk,
    CoverageLimit,
    SweepReport,
    SweepSummary,
)


def telemetry_coverage_event_ids() -> tuple[frozenset[int], frozenset[int]]:
    """Return canonical supported EventID sets used by sweep normalizers."""
    from praetor.correlation.security_log import SUPPORTED_SECURITY_EVENT_IDS
    from praetor.correlation.sysmon import SUPPORTED_SYSMON_EVENT_IDS

    return SUPPORTED_SYSMON_EVENT_IDS, SUPPORTED_SECURITY_EVENT_IDS


def _format_event_id_list(event_ids: frozenset[int]) -> str:
    return ", ".join(str(event_id) for event_id in sorted(event_ids))


def build_sweep_report(summary: SweepSummary) -> SweepReport:
    """Build structured coverage and absence-of-evidence report."""
    counts = summary.event_counts
    sysmon_ids, security_ids = telemetry_coverage_event_ids()
    sysmon_id_text = _format_event_id_list(sysmon_ids)
    security_id_text = _format_event_id_list(security_ids)

    if not summary.has_normalized_evidence:
        observation_window = "No normalized evidence observed in supplied telemetry."
    else:
        observation_window = _observation_window_text(summary)

    coverage_limits = (
        CoverageLimit(
            code="telemetry_sources",
            description=(
                "Sweep normalizes only Windows Sysmon process-create "
                f"(EventID {sysmon_id_text}) and Security successful logon "
                f"(EventID {security_id_text})."
            ),
        ),
        CoverageLimit(
            code="event_volume",
            description=(
                f"Sysmon seen={counts.sysmon_events_seen}, "
                f"normalized={counts.sysmon_events_normalized}, "
                f"skipped={counts.sysmon_events_skipped}; "
                f"Security seen={counts.security_events_seen}, "
                f"normalized={counts.security_events_normalized}, "
                f"skipped={counts.security_events_skipped}."
            ),
        ),
        CoverageLimit(
            code="observation_window",
            description=observation_window,
        ),
        CoverageLimit(
            code="derived_entities",
            description=(
                f"Observed principals={len(summary.principals)}, "
                f"assets={len(summary.assets)}, "
                f"admin_patterns={len(summary.admin_patterns)}."
            ),
        ),
    )

    absence_of_evidence_risks = _build_absence_of_evidence_risks(summary)

    if not summary.has_normalized_evidence:
        summary_text = (
            "Empirical org-config sweep found zero normalized evidence — "
            "proposed artifact is marked unusable and cannot be activated."
        )
    else:
        summary_text = (
            "Empirical org-config sweep prototype — proposed artifact requires "
            "SOC lead review before activation."
        )

    return SweepReport(
        coverage_limits=coverage_limits,
        absence_of_evidence_risks=absence_of_evidence_risks,
        summary_text=summary_text,
    )


def _build_absence_of_evidence_risks(
    summary: SweepSummary,
) -> tuple[AbsenceOfEvidenceRisk, ...]:
    risks: list[AbsenceOfEvidenceRisk] = []

    if not summary.has_normalized_evidence:
        risks.append(
            AbsenceOfEvidenceRisk(
                code="zero_normalized_evidence",
                description=(
                    "No telemetry normalized to evidence facts — sweep output is "
                    "explicitly unusable for activation."
                ),
            )
        )

    ambiguous_total = sum(
        principal.ambiguous_observation_count for principal in summary.principals
    )
    if ambiguous_total > 0:
        risks.append(
            AbsenceOfEvidenceRisk(
                code="principal_identity_ambiguous",
                description=(
                    f"{ambiguous_total} principal observation(s) carried "
                    "EvidenceFact.ambiguity_flag=true (low-confidence identity)."
                ),
            )
        )
    else:
        risks.append(
            AbsenceOfEvidenceRisk(
                code="principal_identity_partial",
                description=(
                    "No ambiguous principal observations in this sweep window, "
                    "but domain-less Sysmon users or uncorroborated Security "
                    "accounts may still appear in broader corpora."
                ),
            )
        )

    if summary.assets:
        subnet_risk = (
            f"Asset subnet_membership is set to {UNOBSERVED_SUBNET_PLACEHOLDER!r} "
            "for all observed hosts — absence of network placement evidence "
            "in v1 telemetry."
        )
        risks.append(
            AbsenceOfEvidenceRisk(
                code="subnet_membership_unobserved",
                description=subnet_risk,
            )
        )

    risks.extend(
        (
            AbsenceOfEvidenceRisk(
                code="never_contain_not_inferred",
                description=(
                    "Proposed artifact retains placeholder never-contain entries only; "
                    "sweep does not infer safe exclusions from absence of malicious "
                    "activity."
                ),
            ),
            AbsenceOfEvidenceRisk(
                code="admin_patterns_heuristic",
                description=(
                    "Normal admin patterns are frequency summaries of "
                    "parent->child process chains and are not validated as benign "
                    "without SOC review."
                ),
            ),
            AbsenceOfEvidenceRisk(
                code="policy_sections_placeholder",
                description=(
                    "Rate limits, breakers, feed policy, and containment statute "
                    "sections copy development defaults — not empirically derived."
                ),
            ),
        )
    )
    return tuple(risks)


def render_sweep_report_markdown(report: SweepReport) -> str:
    """Render human-readable markdown report for SOC review."""
    lines = [
        "# Org-Config Sweep Report",
        "",
        report.summary_text,
        "",
        "## Coverage limits",
        "",
    ]
    for limit in report.coverage_limits:
        lines.append(f"- **{limit.code}**: {limit.description}")
    lines.extend(["", "## Absence-of-evidence risks", ""])
    for risk in report.absence_of_evidence_risks:
        lines.append(f"- **{risk.code}**: {risk.description}")
    lines.append("")
    return "\n".join(lines)


def _observation_window_text(summary: SweepSummary) -> str:
    if summary.earliest_timestamp is None or summary.latest_timestamp is None:
        return "No normalized timestamps observed in supplied telemetry."
    return (
        "Observed normalized event timestamps span "
        f"{summary.earliest_timestamp.isoformat()} to "
        f"{summary.latest_timestamp.isoformat()}."
    )


__all__ = [
    "AbsenceOfEvidenceRisk",
    "CoverageLimit",
    "SweepReport",
    "build_sweep_report",
    "render_sweep_report_markdown",
    "telemetry_coverage_event_ids",
]
