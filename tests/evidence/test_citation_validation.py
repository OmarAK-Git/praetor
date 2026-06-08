from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.evidence.citations import validate_evidence_citations


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="ev-process",
                normalized_fields={
                    "process_name": "cmd.exe",
                    "command_line": "cmd.exe /c whoami",
                    "parent": {"process_name": "services.exe"},
                },
                source_event_reference="sysmon:1:100",
                raw_source='{"Image":"cmd.exe"}',
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=datetime(2026, 6, 8, tzinfo=UTC),
            ),
            EvidenceFact(
                evidence_id="ev-account",
                normalized_fields={"account_name": "jdoe"},
                source_event_reference="security:4624:101",
                raw_source='{"TargetUserName":"jdoe"}',
                provenance_path="windows_security_log",
                ambiguity_flag=True,
                timestamp=datetime(2026, 6, 8, tzinfo=UTC),
            ),
        ]
    )


def _judgment(
    *,
    proposed: Disposition = Disposition.STANDARD_REVIEW,
    refs: list[CitedEvidenceRef] | None = None,
) -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=proposed,
        cited_evidence_refs=[] if refs is None else refs,
        key_tells=["suspicious process"],
        org_config_refs=["containment_policy.default_escalate"],
        benign_alternatives=["admin script"],
        benign_alternatives_ruled_out=["no change window"],
        convergence_reasoning="process behavior matched the alert",
        narrative="cmd.exe launched suspiciously",
        model_name="fake",
        provider_name="test",
    )


def test_valid_evidence_id_and_normalized_field_path_resolve() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="process_name",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is True
    assert result.errors == ()
    assert len(result.resolved) == 1
    assert result.resolved[0].evidence_id == "ev-process"
    assert result.resolved[0].field_path == "process_name"
    assert result.resolved[0].value == "cmd.exe"
    assert result.resolved[0].ambiguity_flag is False


def test_nested_normalized_field_path_resolves() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="parent.process_name",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is True
    assert result.resolved[0].value == "services.exe"


def test_missing_evidence_id_fails_validation() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="missing-ev",
                    field_path="process_name",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors == (
        "missing_evidence_id:missing-ev:process_name",
    )
    assert result.resolved == ()


def test_missing_field_path_fails_validation() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="missing_field",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors == (
        "missing_field_path:ev-process:missing_field",
    )


def test_missing_citations_fail_for_escalate_and_auto_contain() -> None:
    for proposed in (Disposition.ESCALATE, Disposition.AUTO_CONTAIN):
        result = validate_evidence_citations(
            _judgment(proposed=proposed),
            _bundle(),
        )

        assert result.valid is False
        assert result.errors == (
            f"missing_citations:{proposed.value}",
        )


def test_missing_citations_do_not_fail_standard_review() -> None:
    result = validate_evidence_citations(
        _judgment(proposed=Disposition.STANDARD_REVIEW),
        _bundle(),
    )

    assert result.valid is True
    assert result.errors == ()
    assert result.resolved == ()


def test_auto_contain_with_missing_evidence_id_fails() -> None:
    result = validate_evidence_citations(
        _judgment(
            proposed=Disposition.AUTO_CONTAIN,
            refs=[
                CitedEvidenceRef(
                    evidence_id="missing-ev",
                    field_path="process_name",
                )
            ],
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors[0].startswith("missing_evidence_id")
    assert result.resolved == ()


def test_auto_contain_with_missing_field_path_fails() -> None:
    result = validate_evidence_citations(
        _judgment(
            proposed=Disposition.AUTO_CONTAIN,
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="not_a_real_field",
                )
            ],
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors[0].startswith("missing_field_path")


def test_raw_source_top_level_field_path_is_not_citable() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="raw_source",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors == (
        "missing_field_path:ev-process:raw_source",
    )


def test_nested_normalized_raw_source_field_path_is_not_citable() -> None:
    bundle = EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="ev-nested-raw",
                normalized_fields={"raw_source": "attacker-controlled"},
                source_event_reference="sysmon:1:200",
                raw_source='{"Image":"cmd.exe"}',
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=datetime(2026, 6, 8, tzinfo=UTC),
            )
        ]
    )
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-nested-raw",
                    field_path="normalized_fields.raw_source",
                )
            ]
        ),
        bundle,
    )

    assert result.valid is False
    assert result.errors == (
        "missing_field_path:ev-nested-raw:normalized_fields.raw_source",
    )


def test_mixed_valid_and_fabricated_refs_fail_all_or_nothing() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="process_name",
                ),
                CitedEvidenceRef(
                    evidence_id="fabricated-ev",
                    field_path="process_name",
                ),
            ]
        ),
        _bundle(),
    )

    assert result.valid is False
    assert len(result.resolved) == 1
    assert result.resolved[0].evidence_id == "ev-process"
    assert result.errors[0].startswith("missing_evidence_id")


def test_empty_field_path_is_invalid() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors == (
        "missing_field_path:ev-process:",
    )


def test_empty_evidence_id_is_invalid() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="",
                    field_path="process_name",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is False
    assert result.errors[0].startswith("missing_evidence_id")


def test_citable_surface_normalized_and_prompt_visible_metadata() -> None:
    """Pin citable field paths: normalized evidence fields plus prompt excerpts.

    ``source_event_reference`` and ``provenance_path`` are provider-visible via
    TASK-014 excerpts. Bare normalized keys (e.g. ``process_name``) are the
    shorthand used by walking-skeleton fixtures. Top-level ``evidence_id`` is
    not a citable field path even though it appears on the fact envelope.
    """
    for field_path in (
        "process_name",
        "normalized_fields.process_name",
        "parent.process_name",
        "source_event_reference",
        "provenance_path",
    ):
        result = validate_evidence_citations(
            _judgment(
                refs=[
                    CitedEvidenceRef(
                        evidence_id="ev-process",
                        field_path=field_path,
                    )
                ]
            ),
            _bundle(),
        )
        assert result.valid is True, field_path

    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-process",
                    field_path="evidence_id",
                )
            ]
        ),
        _bundle(),
    )
    assert result.valid is False
    assert result.errors == (
        "missing_field_path:ev-process:evidence_id",
    )


def test_ambiguity_flag_is_exposed_on_resolved_citation() -> None:
    result = validate_evidence_citations(
        _judgment(
            refs=[
                CitedEvidenceRef(
                    evidence_id="ev-account",
                    field_path="account_name",
                )
            ]
        ),
        _bundle(),
    )

    assert result.valid is True
    assert result.resolved[0].ambiguity_flag is True
