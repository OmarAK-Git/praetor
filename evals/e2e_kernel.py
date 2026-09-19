"""Sprint 1 E2E eval kernel (spec §4). Sibling of evals.harness."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from evals.scorecard import Realm, ScorecardRow, validate_scorecard_row

EVALS_DIR = Path(__file__).resolve().parent
E2E_SCENARIOS_DIR = EVALS_DIR / "e2e_scenarios"

REQUIRED_E2E_SCENARIO_IDS: frozenset[str] = frozenset(
    {
        "cap.baseline_bag_path_a",
        "cap.stump_parity_guard",
        "cap.no_label_leak_ids",
        "gov.never_contain_live_shape",
        "gov.feed_unhealthy_blocks_contain",
        "gov.recovery_never_contains",
        "des.envelope_rejects_extra_fields",
        "des.path_b_stays_out_of_src",
        "des.evidence_hash_stable",
        "thr.instruction_in_cmdline",
        "thr.valid_cite_wrong_process",
        "thr.ambiguous_multi_host_target",
        "use.reconstruct_from_ledger",
        "use.progressive_auth_report",
        "use.demo_honesty_gate",
    }
)

_REALM_BY_PREFIX: dict[str, Realm] = {
    "cap": "capability",
    "gov": "governance",
    "des": "design",
    "thr": "threat",
    "use": "usability",
}


def missing_required_scenario_ids(present: set[str]) -> frozenset[str]:
    return REQUIRED_E2E_SCENARIO_IDS - present


def scorecards_for_missing_ids(missing: frozenset[str]) -> list[ScorecardRow]:
    rows: list[ScorecardRow] = []
    for scenario_id in sorted(missing):
        prefix = scenario_id.split(".", 1)[0]
        row = ScorecardRow(
            schema_version="1",
            scenario_id=scenario_id,
            realm=_REALM_BY_PREFIX[prefix],
            arm="old_build",
            status="error",
            failure_class="harness",
            expected={"present": True},
            observed={"present": False},
            provider="fake",
            notes="missing scenario file",
        )
        rows.append(validate_scorecard_row(row))
    return rows


def kernel_exit_code(rows: Sequence[ScorecardRow]) -> int:
    present_pairs = {(row.scenario_id, row.arm) for row in rows}
    for scenario_id in REQUIRED_E2E_SCENARIO_IDS:
        if (scenario_id, "old_build") not in present_pairs and (
            scenario_id,
            "new_build",
        ) not in present_pairs:
            return 1
    if any(row.status in {"fail", "error"} for row in rows):
        return 1
    return 0


def run_e2e_kernel(
    *,
    tmp_root: Path,
    scenarios_dir: Path | None = None,
) -> list[ScorecardRow]:
    _ = tmp_root
    directory = scenarios_dir or E2E_SCENARIOS_DIR
    present = {path.stem for path in directory.glob("*.yaml")}
    return scorecards_for_missing_ids(missing_required_scenario_ids(present))


def format_scorecards(rows: Sequence[ScorecardRow]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.append(
            f"[{row.status.upper()}] {row.scenario_id} {row.arm} "
            f"failure_class={row.failure_class}"
        )
        if row.notes:
            lines.append(f"  - {row.notes}")
    return "\n".join(lines)
