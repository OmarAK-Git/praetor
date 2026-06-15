"""Hardcoded walking-skeleton evidence catalog and judgment fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.engine.ids import hash_evidence_bundle

SKELETON_ALERT_ID = "ALERT-SKELETON-001"
SKELETON_EVIDENCE_ID = "ev-skeleton-1"

SKELETON_EVIDENCE_CATALOG: dict[str, dict[str, Any]] = {
    SKELETON_EVIDENCE_ID: {
        "evidence_id": SKELETON_EVIDENCE_ID,
        "process_name": "cmd.exe",
        "provenance_path": "synthetic/walking_skeleton",
        "ambiguity_flag": False,
    },
}

SKELETON_EVIDENCE_BUNDLE = EvidenceBundle(
    facts=[
        EvidenceFact(
            evidence_id=SKELETON_EVIDENCE_ID,
            normalized_fields={"process_name": "cmd.exe"},
            source_event_reference="synthetic:walking-skeleton",
            raw_source="synthetic walking skeleton event",
            provenance_path="synthetic/walking_skeleton",
            ambiguity_flag=False,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
)

SKELETON_BUNDLE_BODY: dict[str, Any] = {
    "schema_version": "1.0",
    "facts": [fact.model_dump(mode="json") for fact in SKELETON_EVIDENCE_BUNDLE.facts],
}

SKELETON_BUNDLE_HASH: str = hash_evidence_bundle(SKELETON_EVIDENCE_BUNDLE)


def skeleton_model_judgment(
    *,
    proposed: Disposition = Disposition.STANDARD_REVIEW,
    cited_refs: list[CitedEvidenceRef] | None = None,
) -> ModelJudgment:
    refs = cited_refs
    if refs is None:
        refs = [
            CitedEvidenceRef(
                evidence_id=SKELETON_EVIDENCE_ID,
                field_path="process_name",
            ),
        ]
    return ModelJudgment(
        proposed_disposition=proposed,
        cited_evidence_refs=refs,
        key_tells=["walking-skeleton"],
        org_config_refs=["containment_policy.default_escalate"],
        benign_alternatives=["scheduled task"],
        benign_alternatives_ruled_out=["none"],
        convergence_reasoning="skeleton fixture",
        narrative="walking skeleton judgment",
        model_name="skeleton",
        provider_name="hardcoded",
    )
