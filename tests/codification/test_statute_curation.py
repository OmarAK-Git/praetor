"""V2-035: statute curation workflow — review-only proposed artifacts."""

from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest
import yaml
from tests.config.shared import EXAMPLE_CONFIG

from praetor.codification.models import PROPOSED_STATUTE_ARTIFACT_KIND
from praetor.codification.placeholders import (
    is_proposed_org_config_artifact,
    is_proposed_statute_artifact,
)
from praetor.codification.statute_curation import (
    SourceAnnotationRef,
    StatuteEdit,
    apply_statute_edits,
    build_proposed_statute_artifact,
    build_statute_curation_workflow,
    render_proposed_statute_yaml,
    render_statute_curation_workflow_json,
    statute_curation_workflow_from_json,
)
from praetor.config.errors import PreflightError
from praetor.config.loader import load_org_config_source
from praetor.config.preflight import run_preflight


def _example_base() -> dict:
    return copy.deepcopy(load_org_config_source(EXAMPLE_CONFIG).document)


def _sample_annotation() -> SourceAnnotationRef:
    return SourceAnnotationRef(
        decision_id="dec-curate-1",
        annotation_id=42,
        disposition_correct=False,
        comment="eng pool should auto-contain",
        reviewer_identity="analyst-1",
        timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )


def _sample_edit() -> StatuteEdit:
    base = _example_base()
    patterns = copy.deepcopy(base["normal_admin_patterns"])
    patterns["patterns"] = list(patterns["patterns"]) + [
        {
            "name": "annotation_derived_eng_jumphost",
            "description": "SOC-confirmed admin pattern from annotation review",
        }
    ]
    return StatuteEdit(
        section="normal_admin_patterns",
        content=patterns,
        rationale="Sustained annotation evidence supports adding eng jumphost pattern",
        source_decision_ids=("dec-curate-1",),
    )


def test_proposed_statute_artifact_is_review_only_and_not_activatable() -> None:
    base = _example_base()
    annotation = _sample_annotation()
    edit = _sample_edit()
    proposed = build_proposed_statute_artifact(
        base,
        edits=[edit],
        source_annotations=[annotation],
        workflow_id="wf-001",
        config_version="statute-proposed-1.1.0",
    )

    assert is_proposed_statute_artifact(proposed)
    assert is_proposed_org_config_artifact(proposed)
    assert (
        proposed["version_metadata"]["artifact_kind"] == PROPOSED_STATUTE_ARTIFACT_KIND
    )
    assert (
        proposed["version_metadata"]["activation_status"] == "proposed_for_review_only"
    )
    assert proposed["version_metadata"]["curation_workflow_id"] == "wf-001"

    yaml_text = render_proposed_statute_yaml(proposed)
    with pytest.raises(PreflightError) as exc_info:
        run_preflight(proposed, verbatim_text=yaml_text)
    assert exc_info.value.code == "proposed_artifact_not_activatable"


def test_workflow_artifact_captures_annotations_edits_reviewer_activation_slot() -> (
    None
):
    base = _example_base()
    annotation = _sample_annotation()
    edit = _sample_edit()
    workflow = build_statute_curation_workflow(
        workflow_id="wf-002",
        base_config=base,
        edits=[edit],
        source_annotations=[annotation],
        reviewer="soc-lead-1",
        config_version="statute-proposed-1.2.0",
    )

    assert workflow.workflow_id == "wf-002"
    assert workflow.reviewer == "soc-lead-1"
    assert len(workflow.source_annotations) == 1
    assert workflow.source_annotations[0].decision_id == "dec-curate-1"
    assert len(workflow.proposed_edits) == 1
    assert workflow.proposed_edits[0].section == "normal_admin_patterns"
    assert workflow.activation_audit is None
    assert is_proposed_statute_artifact(workflow.proposed_config)

    payload = render_statute_curation_workflow_json(workflow)
    restored = statute_curation_workflow_from_json(payload)
    assert restored.workflow_id == workflow.workflow_id
    assert restored.reviewer == workflow.reviewer
    assert restored.source_annotations[0].annotation_id == 42
    assert restored.proposed_edits[0].rationale == edit.rationale
    assert restored.activation_audit is None


def test_apply_statute_edits_rejects_non_curatable_section() -> None:
    base = _example_base()
    bad_edit = StatuteEdit(
        section="business_context",
        content={"notes": "not allowed"},
        rationale="should fail",
        source_decision_ids=(),
    )
    with pytest.raises(ValueError, match="not a curatable statute section"):
        apply_statute_edits(base, [bad_edit])


def test_activation_ready_stripped_config_passes_preflight() -> None:
    base = _example_base()
    workflow = build_statute_curation_workflow(
        workflow_id="wf-003",
        base_config=base,
        edits=[_sample_edit()],
        source_annotations=[_sample_annotation()],
        config_version="statute-proposed-1.3.0",
    )
    ready = copy.deepcopy(workflow.proposed_config)
    metadata = ready["version_metadata"]
    for key in (
        "artifact_kind",
        "activation_status",
        "artifact_usable",
        "curation_workflow_id",
    ):
        metadata.pop(key, None)

    yaml_text = render_proposed_statute_yaml(ready)
    snapshot = run_preflight(ready, verbatim_text=yaml_text)
    patterns = snapshot.normal_admin_patterns.patterns
    last_pattern = patterns[-1]
    pattern_name = (
        last_pattern["name"] if isinstance(last_pattern, dict) else last_pattern.name
    )
    assert pattern_name == "annotation_derived_eng_jumphost"


def test_workflow_json_round_trip_preserves_proposed_config() -> None:
    workflow = build_statute_curation_workflow(
        workflow_id="wf-004",
        base_config=_example_base(),
        edits=[_sample_edit()],
        source_annotations=[_sample_annotation()],
        config_version="statute-proposed-1.4.0",
    )
    restored = statute_curation_workflow_from_json(
        render_statute_curation_workflow_json(workflow)
    )
    assert yaml.safe_load(render_proposed_statute_yaml(restored.proposed_config)) == (
        yaml.safe_load(render_proposed_statute_yaml(workflow.proposed_config))
    )
