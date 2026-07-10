"""V2-035: SOC-lead statute curation promotion and activation audit."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN

from praetor.auth import InsufficientRoleError
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.codification.statute_curation import (
    SourceAnnotationRef,
    StatuteEdit,
    build_statute_curation_workflow,
)
from praetor.config.activation import promote_statute_curation
from praetor.config.errors import ActivationError
from praetor.config.loader import load_org_config_source
from praetor.config.state import fetch_active_org_config
from praetor.state.store import StateStore


def _example_base() -> dict:
    return copy.deepcopy(load_org_config_source(EXAMPLE_CONFIG).document)


def _workflow_with_edit() -> object:
    base = _example_base()
    patterns = copy.deepcopy(base["normal_admin_patterns"])
    patterns["patterns"] = list(patterns["patterns"]) + [
        {
            "name": "annotation_derived_eng_jumphost",
            "description": "SOC-confirmed admin pattern from annotation review",
        }
    ]
    edit = StatuteEdit(
        section="normal_admin_patterns",
        content=patterns,
        rationale="Promotion after annotation review",
        source_decision_ids=("dec-promote-1",),
    )
    annotation = SourceAnnotationRef(
        decision_id="dec-promote-1",
        annotation_id=7,
        disposition_correct=False,
        comment="model too conservative on eng pool",
        reviewer_identity="analyst-2",
        timestamp=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
    )
    return build_statute_curation_workflow(
        workflow_id="wf-promote-1",
        base_config=base,
        edits=[edit],
        source_annotations=[annotation],
        reviewer="soc-lead-1",
        config_version="statute-promoted-2.0.0",
    )


def test_soc_lead_promotion_runs_preflight_and_records_activation_audit(
    store: StateStore, verifier: PrincipalMapVerifier, tmp_path: Path
) -> None:
    workflow = _workflow_with_edit()
    updated, activation = promote_statute_curation(
        store,
        workflow,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
    )

    assert activation.snapshot_hash
    assert updated.activation_audit is not None
    audit = updated.activation_audit
    assert audit.workflow_id == "wf-promote-1"
    assert audit.reviewer == "soc-lead-1"
    assert audit.snapshot_hash == activation.snapshot_hash
    assert audit.activated_at.tzinfo is not None

    active = fetch_active_org_config(store.conn)
    assert active is not None
    assert active.snapshot_hash == activation.snapshot_hash


def test_promotion_rejects_review_only_proposed_artifact_without_stripping(
    store: StateStore, verifier: PrincipalMapVerifier
) -> None:
    workflow = _workflow_with_edit()
    with pytest.raises(ActivationError) as exc_info:
        promote_statute_curation(
            store,
            workflow,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            activation_ready=False,
        )
    assert exc_info.value.code == "proposed_artifact_not_activatable"


def test_wrong_role_rejected_for_statute_promotion(
    store: StateStore, tmp_path: Path
) -> None:
    analyst = Principal(identity="analyst-1", role="analyst")
    bad_verifier = PrincipalMapVerifier({"t": analyst})
    workflow = _workflow_with_edit()
    with pytest.raises(InsufficientRoleError):
        promote_statute_curation(
            store,
            workflow,
            token="t",
            verifier=bad_verifier,
        )


def test_promotion_writes_activation_ready_yaml_to_disk(
    store: StateStore, verifier: PrincipalMapVerifier, tmp_path: Path
) -> None:
    workflow = _workflow_with_edit()
    output = tmp_path / "promoted.yaml"
    promote_statute_curation(
        store,
        workflow,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
        output_path=output,
    )
    assert output.is_file()
    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert "artifact_kind" not in parsed.get("version_metadata", {})
    assert parsed["normal_admin_patterns"]["patterns"][-1]["name"] == (
        "annotation_derived_eng_jumphost"
    )
