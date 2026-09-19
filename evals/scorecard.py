"""E2E kernel scorecard row (spec §4)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ScorecardStatus = Literal["pass", "fail", "pending", "error"]
FailureClass = Literal["none", "harness", "model", "theater_detector"]
Realm = Literal["capability", "governance", "design", "threat", "usability"]
Arm = Literal["old_build", "new_build"]
ProviderKind = Literal["fake", "vertex"]

CAPABILITY_QUALITY_IDS: frozenset[str] = frozenset(
    {"cap.baseline_bag_path_a", "cap.stump_parity_guard"}
)


class ScorecardValidationError(ValueError):
    """Scorecard honesty rules failed."""


class ScorecardRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"]
    scenario_id: str
    realm: Realm
    arm: Arm
    status: ScorecardStatus
    failure_class: FailureClass
    expected: dict[str, Any]
    observed: dict[str, Any]
    provider: ProviderKind
    notes: str = ""


def validate_scorecard_row(row: ScorecardRow) -> ScorecardRow:
    if row.status == "pending":
        legal = (
            row.scenario_id in CAPABILITY_QUALITY_IDS and row.arm == "new_build"
        )
        if not legal:
            msg = (
                "pending is legal only for capability quality new_build "
                f"({sorted(CAPABILITY_QUALITY_IDS)}); got "
                f"{row.scenario_id!r} arm={row.arm!r}"
            )
            raise ScorecardValidationError(msg)
    if row.status in {"pass", "pending"} and row.failure_class != "none":
        msg = f"failure_class must be none when status={row.status!r}"
        raise ScorecardValidationError(msg)
    if row.status in {"fail", "error"} and row.failure_class == "none":
        msg = f"failure_class is required when status={row.status!r}"
        raise ScorecardValidationError(msg)
    return row
