"""ModelJudgment/DecisionEdict.session_trace_hash backward compatibility
and pass-through (DEC-064, Task 13/14 of
docs/superpowers/plans/2026-07-30-agentic-judgment.md)."""

from __future__ import annotations

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment


def _judgment(session_trace_hash: str | None = None) -> ModelJudgment:
    return ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
        session_trace_hash=session_trace_hash,
    )


def test_model_judgment_session_trace_hash_defaults_to_none() -> None:
    judgment = ModelJudgment(
        proposed_disposition=Disposition.STANDARD_REVIEW,
        cited_evidence_refs=[],
        key_tells=[],
        org_config_refs=[],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="none",
        narrative="none",
        model_name="fake",
        provider_name="fake",
    )
    assert judgment.session_trace_hash is None


def test_model_judgment_session_trace_hash_round_trips() -> None:
    judgment = _judgment(session_trace_hash="deadbeef" * 8)
    assert judgment.session_trace_hash == "deadbeef" * 8
