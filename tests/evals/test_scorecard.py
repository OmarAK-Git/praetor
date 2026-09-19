from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.scorecard import (
    CAPABILITY_QUALITY_IDS,
    ScorecardRow,
    ScorecardValidationError,
    validate_scorecard_row,
)
from pydantic import ValidationError

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "evals" / "schemas" / "scorecard_schema.json"
)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1",
        "scenario_id": "gov.never_contain_live_shape",
        "realm": "governance",
        "arm": "old_build",
        "status": "pass",
        "failure_class": "none",
        "expected": {"final_disposition": "escalate"},
        "observed": {"final_disposition": "escalate"},
        "provider": "fake",
        "notes": "",
    }
    payload.update(overrides)
    return payload


def test_schema_additional_properties_false() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "schema_version",
        "scenario_id",
        "realm",
        "arm",
        "status",
        "failure_class",
        "expected",
        "observed",
        "provider",
    ]


def test_row_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ScorecardRow.model_validate(_valid_payload(skip_reason="do-not-allow"))


def test_pending_legal_only_for_capability_quality_new_build() -> None:
    row = ScorecardRow.model_validate(
        _valid_payload(
            scenario_id="cap.baseline_bag_path_a",
            realm="capability",
            arm="new_build",
            status="pending",
            failure_class="none",
        )
    )
    assert validate_scorecard_row(row).status == "pending"
    assert "cap.stump_parity_guard" in CAPABILITY_QUALITY_IDS


def test_pending_illegal_for_leak_pin_and_non_quality() -> None:
    with pytest.raises(ScorecardValidationError, match="pending"):
        validate_scorecard_row(
            ScorecardRow.model_validate(
                _valid_payload(
                    scenario_id="cap.no_label_leak_ids",
                    realm="capability",
                    arm="new_build",
                    status="pending",
                    failure_class="none",
                )
            )
        )
    with pytest.raises(ScorecardValidationError, match="pending"):
        validate_scorecard_row(
            ScorecardRow.model_validate(
                _valid_payload(status="pending", failure_class="none")
            )
        )


def test_failure_class_none_when_pass_or_pending() -> None:
    with pytest.raises(ScorecardValidationError, match="failure_class"):
        validate_scorecard_row(
            ScorecardRow.model_validate(_valid_payload(failure_class="model"))
        )


def test_failure_class_required_when_fail_or_error() -> None:
    with pytest.raises(ScorecardValidationError, match="failure_class"):
        validate_scorecard_row(
            ScorecardRow.model_validate(
                _valid_payload(status="fail", failure_class="none")
            )
        )
    row = validate_scorecard_row(
        ScorecardRow.model_validate(
            _valid_payload(status="error", failure_class="harness")
        )
    )
    assert row.failure_class == "harness"
