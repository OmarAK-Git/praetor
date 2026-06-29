"""V2-004: provider_unavailable Outcome Matrix enum and metrics alignment."""

from __future__ import annotations

from evals.outcome_matrix import OUTCOME_MATRIX_SFE

from praetor.metrics.events import LLM_FAILURE_FAULT_FLAGS, OutcomeMatrixFaultFlag


def test_provider_unavailable_in_outcome_matrix_enum() -> None:
    assert OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE.value == "provider_unavailable"


def test_provider_unavailable_sfe_polarity() -> None:
    assert OUTCOME_MATRIX_SFE[OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE] is True


def test_provider_unavailable_in_llm_failure_fault_flags() -> None:
    assert OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE in LLM_FAILURE_FAULT_FLAGS
