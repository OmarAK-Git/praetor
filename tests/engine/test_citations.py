"""Direct unit coverage for the engine.citations adapter (DEBT-072).

evidence/citations.py already has full branch coverage in
tests/evidence/test_citation_validation.py; this file only pins that the
engine-facing adapter forwards to it correctly, since engine/citations.py
was previously exercised only indirectly through orchestrator integration
tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.engine.citations import validate_skeleton_citations

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)


def _fact(evidence_id: str = "ev-1") -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"process_name": "cmd.exe"},
        source_event_reference="sysmon:1",
        raw_source="raw",
        provenance_path="sysmon_event_log",
        ambiguity_flag=False,
        timestamp=NOW,
    )


def _judgment(refs: list[CitedEvidenceRef]) -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.ESCALATE,
        cited_evidence_refs=refs,
        key_tells=["tell"],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="reasoning",
        narrative="narrative",
        model_name="fake-model",
        provider_name="fake-provider",
    )


def test_validate_skeleton_citations_true_for_resolvable_citation() -> None:
    bundle = EvidenceBundle(facts=[_fact()])
    judgment = _judgment(
        [CitedEvidenceRef(evidence_id="ev-1", field_path="normalized_fields.process_name")]
    )

    assert validate_skeleton_citations(judgment, bundle) is True


def test_validate_skeleton_citations_false_for_unresolvable_evidence_id() -> None:
    bundle = EvidenceBundle(facts=[_fact()])
    judgment = _judgment(
        [CitedEvidenceRef(evidence_id="ev-missing", field_path="normalized_fields.process_name")]
    )

    assert validate_skeleton_citations(judgment, bundle) is False


def test_validate_skeleton_citations_false_for_unresolvable_field_path() -> None:
    bundle = EvidenceBundle(facts=[_fact()])
    judgment = _judgment(
        [CitedEvidenceRef(evidence_id="ev-1", field_path="normalized_fields.no_such_field")]
    )

    assert validate_skeleton_citations(judgment, bundle) is False
