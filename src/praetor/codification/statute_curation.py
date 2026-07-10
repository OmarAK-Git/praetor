"""Annotation-driven statute curation workflow (V2-035)."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yaml

from praetor.codification.models import (
    PROPOSED_STATUTE_ARTIFACT_KIND,
    STATUTE_CURATABLE_SECTIONS,
)


@dataclass(frozen=True)
class SourceAnnotationRef:
    decision_id: str
    annotation_id: int
    disposition_correct: bool
    comment: str
    reviewer_identity: str
    timestamp: datetime


@dataclass(frozen=True)
class StatuteEdit:
    section: str
    content: dict[str, Any]
    rationale: str
    source_decision_ids: tuple[str, ...]


@dataclass(frozen=True)
class StatuteCurationActivationAudit:
    workflow_id: str
    reviewer: str
    snapshot_hash: str
    activated_at: datetime
    revoked_directive_ids: tuple[str, ...]
    retired_emergency_entry_ids: tuple[str, ...]
    emitted_alert_ids: tuple[str, ...]
    health_alert_batch_id: str


@dataclass(frozen=True)
class StatuteCurationWorkflow:
    workflow_id: str
    source_annotations: tuple[SourceAnnotationRef, ...]
    proposed_edits: tuple[StatuteEdit, ...]
    reviewer: str | None
    proposed_config: dict[str, Any]
    activation_audit: StatuteCurationActivationAudit | None = None


def apply_statute_edits(
    base_config: Mapping[str, Any],
    edits: Sequence[StatuteEdit],
) -> dict[str, Any]:
    """Apply explicit statute section replacements to a base org-config document."""
    result = copy.deepcopy(dict(base_config))
    for edit in edits:
        if edit.section not in STATUTE_CURATABLE_SECTIONS:
            msg = f"{edit.section!r} is not a curatable statute section"
            raise ValueError(msg)
        result[edit.section] = copy.deepcopy(edit.content)
    return result


def build_proposed_statute_artifact(
    base_config: Mapping[str, Any],
    *,
    edits: Sequence[StatuteEdit],
    source_annotations: Sequence[SourceAnnotationRef],
    workflow_id: str,
    config_version: str,
) -> dict[str, Any]:
    """Build a review-only proposed statute artifact from annotations and edits."""
    if not source_annotations:
        msg = "statute curation requires at least one source annotation"
        raise ValueError(msg)
    if not edits:
        msg = "statute curation requires at least one proposed edit"
        raise ValueError(msg)

    config = apply_statute_edits(base_config, edits)
    metadata = dict(config.get("version_metadata", {}))
    metadata.update(
        {
            "config_version": config_version,
            "artifact_kind": PROPOSED_STATUTE_ARTIFACT_KIND,
            "activation_status": "proposed_for_review_only",
            "artifact_usable": True,
            "curation_workflow_id": workflow_id,
        }
    )
    config["version_metadata"] = metadata
    return config


def build_statute_curation_workflow(
    *,
    workflow_id: str,
    base_config: Mapping[str, Any],
    edits: Sequence[StatuteEdit],
    source_annotations: Sequence[SourceAnnotationRef],
    config_version: str,
    reviewer: str | None = None,
) -> StatuteCurationWorkflow:
    """Assemble a tracked workflow artifact for SOC review and promotion."""
    proposed_config = build_proposed_statute_artifact(
        base_config,
        edits=edits,
        source_annotations=source_annotations,
        workflow_id=workflow_id,
        config_version=config_version,
    )
    return StatuteCurationWorkflow(
        workflow_id=workflow_id,
        source_annotations=tuple(source_annotations),
        proposed_edits=tuple(edits),
        reviewer=reviewer,
        proposed_config=proposed_config,
        activation_audit=None,
    )


def render_proposed_statute_yaml(proposed_config: Mapping[str, Any]) -> str:
    """Render proposed statute artifact as YAML for SOC review."""
    return yaml.safe_dump(
        dict(proposed_config),
        sort_keys=False,
        allow_unicode=True,
    )


def _serialize_annotation(annotation: SourceAnnotationRef) -> dict[str, Any]:
    return {
        "decision_id": annotation.decision_id,
        "annotation_id": annotation.annotation_id,
        "disposition_correct": annotation.disposition_correct,
        "comment": annotation.comment,
        "reviewer_identity": annotation.reviewer_identity,
        "timestamp": annotation.timestamp.isoformat(),
    }


def _deserialize_annotation(payload: Mapping[str, Any]) -> SourceAnnotationRef:
    timestamp = datetime.fromisoformat(str(payload["timestamp"]))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return SourceAnnotationRef(
        decision_id=str(payload["decision_id"]),
        annotation_id=int(payload["annotation_id"]),
        disposition_correct=bool(payload["disposition_correct"]),
        comment=str(payload["comment"]),
        reviewer_identity=str(payload["reviewer_identity"]),
        timestamp=timestamp,
    )


def _serialize_edit(edit: StatuteEdit) -> dict[str, Any]:
    return {
        "section": edit.section,
        "content": edit.content,
        "rationale": edit.rationale,
        "source_decision_ids": list(edit.source_decision_ids),
    }


def _deserialize_edit(payload: Mapping[str, Any]) -> StatuteEdit:
    return StatuteEdit(
        section=str(payload["section"]),
        content=copy.deepcopy(dict(payload["content"])),
        rationale=str(payload["rationale"]),
        source_decision_ids=tuple(str(item) for item in payload["source_decision_ids"]),
    )


def _serialize_activation_audit(
    audit: StatuteCurationActivationAudit,
) -> dict[str, Any]:
    return {
        "workflow_id": audit.workflow_id,
        "reviewer": audit.reviewer,
        "snapshot_hash": audit.snapshot_hash,
        "activated_at": audit.activated_at.isoformat(),
        "revoked_directive_ids": list(audit.revoked_directive_ids),
        "retired_emergency_entry_ids": list(audit.retired_emergency_entry_ids),
        "emitted_alert_ids": list(audit.emitted_alert_ids),
        "health_alert_batch_id": audit.health_alert_batch_id,
    }


def _deserialize_activation_audit(
    payload: Mapping[str, Any],
) -> StatuteCurationActivationAudit:
    activated_at = datetime.fromisoformat(str(payload["activated_at"]))
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=UTC)
    return StatuteCurationActivationAudit(
        workflow_id=str(payload["workflow_id"]),
        reviewer=str(payload["reviewer"]),
        snapshot_hash=str(payload["snapshot_hash"]),
        activated_at=activated_at,
        revoked_directive_ids=tuple(
            str(item) for item in payload["revoked_directive_ids"]
        ),
        retired_emergency_entry_ids=tuple(
            str(item) for item in payload["retired_emergency_entry_ids"]
        ),
        emitted_alert_ids=tuple(str(item) for item in payload["emitted_alert_ids"]),
        health_alert_batch_id=str(payload["health_alert_batch_id"]),
    )


def render_statute_curation_workflow_json(workflow: StatuteCurationWorkflow) -> str:
    """Serialize workflow artifact for operator review and audit retention."""
    payload: dict[str, Any] = {
        "workflow_id": workflow.workflow_id,
        "reviewer": workflow.reviewer,
        "source_annotations": [
            _serialize_annotation(item) for item in workflow.source_annotations
        ],
        "proposed_edits": [_serialize_edit(item) for item in workflow.proposed_edits],
        "proposed_config": workflow.proposed_config,
        "activation_audit": (
            _serialize_activation_audit(workflow.activation_audit)
            if workflow.activation_audit is not None
            else None
        ),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def statute_curation_workflow_from_json(payload: str) -> StatuteCurationWorkflow:
    """Restore a workflow artifact from JSON."""
    document = json.loads(payload)
    if not isinstance(document, dict):
        msg = "workflow artifact must be a JSON object"
        raise ValueError(msg)

    audit_payload = document.get("activation_audit")
    activation_audit = (
        _deserialize_activation_audit(audit_payload)
        if isinstance(audit_payload, Mapping)
        else None
    )
    annotations_raw = document.get("source_annotations", [])
    edits_raw = document.get("proposed_edits", [])
    proposed_config = document.get("proposed_config")
    if not isinstance(annotations_raw, list) or not isinstance(edits_raw, list):
        msg = "workflow artifact has invalid annotations or edits"
        raise ValueError(msg)
    if not isinstance(proposed_config, dict):
        msg = "workflow artifact missing proposed_config"
        raise ValueError(msg)

    return StatuteCurationWorkflow(
        workflow_id=str(document["workflow_id"]),
        source_annotations=tuple(
            _deserialize_annotation(item)
            for item in annotations_raw
            if isinstance(item, Mapping)
        ),
        proposed_edits=tuple(
            _deserialize_edit(item) for item in edits_raw if isinstance(item, Mapping)
        ),
        reviewer=(
            str(document["reviewer"]) if document.get("reviewer") is not None else None
        ),
        proposed_config=proposed_config,
        activation_audit=activation_audit,
    )


def activation_ready_config(proposed_config: Mapping[str, Any]) -> dict[str, Any]:
    """Strip review-only markers so SOC-lead promotion can run full preflight."""
    config = copy.deepcopy(dict(proposed_config))
    metadata = config.get("version_metadata")
    if not isinstance(metadata, dict):
        msg = "proposed statute artifact missing version_metadata"
        raise ValueError(msg)
    for key in (
        "artifact_kind",
        "activation_status",
        "artifact_usable",
        "curation_workflow_id",
    ):
        metadata.pop(key, None)
    return config


def with_activation_audit(
    workflow: StatuteCurationWorkflow,
    audit: StatuteCurationActivationAudit,
) -> StatuteCurationWorkflow:
    """Return workflow artifact with activation audit trail recorded."""
    return StatuteCurationWorkflow(
        workflow_id=workflow.workflow_id,
        source_annotations=workflow.source_annotations,
        proposed_edits=workflow.proposed_edits,
        reviewer=workflow.reviewer,
        proposed_config=workflow.proposed_config,
        activation_audit=audit,
    )


__all__ = [
    "SourceAnnotationRef",
    "StatuteCurationActivationAudit",
    "StatuteCurationWorkflow",
    "StatuteEdit",
    "activation_ready_config",
    "apply_statute_edits",
    "build_proposed_statute_artifact",
    "build_statute_curation_workflow",
    "render_proposed_statute_yaml",
    "render_statute_curation_workflow_json",
    "statute_curation_workflow_from_json",
    "with_activation_audit",
]
