"""Coverage and risk reporting for org-config sweeps."""

from __future__ import annotations

from praetor.codification.models import (
    UNOBSERVED_SUBNET_PLACEHOLDER,
    AbsenceOfEvidenceRisk,
    CoverageLimit,
    SweepReport,
    SweepSummary,
)

SUPPORTED_SYSMON_EVENT_IDS = (1,)
SUPPORTED_SECURITY_EVENT_IDS = (4624,)


def build_sweep_report(summary: SweepSummary) -> SweepReport:
    """Build structured coverage and absence-of-evidence report."""
    counts = summary.event_counts
    sysmon_id = SUPPORTED_SYSMON_EVENT_IDS[0]
    security_id = SUPPORTED_SECURITY_EVENT_IDS[0]
    coverage_limits = (
        CoverageLimit(
            code="telemetry_sources",
            description=(
                "Sweep normalizes only Windows Sysmon process-create "
                f"(EventID {sysmon_id}) and Security successful logon "
                f"(EventID {security_id})."
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
            description=_observation_window_text(summary),
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

    subnet_risk = (
        f"Asset subnet_membership is set to {UNOBSERVED_SUBNET_PLACEHOLDER!r} "
        "for all observed hosts — absence of network placement evidence "
        "in v1 telemetry."
    )
    absence_of_evidence_risks = (
        AbsenceOfEvidenceRisk(
            code="subnet_membership_unobserved",
            description=subnet_risk,
        ),
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
            code="principal_identity_partial",
            description=(
                "Domain-less Sysmon users and Security accounts without "
                "corroboration may represent incomplete identity coverage."
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

    summary_text = (
        "Empirical org-config sweep prototype — proposed artifact requires "
        "SOC lead review before activation."
    )
    return SweepReport(
        coverage_limits=coverage_limits,
        absence_of_evidence_risks=absence_of_evidence_risks,
        summary_text=summary_text,
    )


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
]
