"""DecisionEdict fault-flag validation at construction (V2-016)."""

from __future__ import annotations

import pytest
from tests.policy.conftest import NOW

from praetor.contracts.disposition import Disposition
from praetor.contracts.fault_flags import InvalidDecisionEdictFaultFlagError
from praetor.engine.edict import build_decision_edict, escalate_disposition
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.metrics.events import OutcomeMatrixFaultFlag
from praetor.policy.containment_policy import NEVER_CONTAIN_SNAPSHOT
from praetor.state.attempts import AttemptState, ProcessingAttempt


def _attempt() -> ProcessingAttempt:
    return ProcessingAttempt(
        processing_attempt_identity="1",
        alert_identity="ALERT-FAULT-FLAG-TEST",
        evidence_bundle_hash="hash",
        org_config_snapshot_hash="snap",
        state=AttemptState.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def test_build_decision_edict_rejects_unknown_fault_flag() -> None:
    disposition = escalate_disposition(
        proposed=Disposition.AUTO_CONTAIN,
        fault_flag="not_in_outcome_matrix",
        system_fault=False,
    )
    with pytest.raises(
        InvalidDecisionEdictFaultFlagError, match="not in OutcomeMatrixFaultFlag"
    ):
        build_decision_edict(
            attempt=_attempt(),
            judgment=skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN),
            disposition=disposition,
            live_never_contain_entries=[],
            stamp_status="not_required",
            ticket_stamp_payload={},
        )


def test_build_decision_edict_rejects_invalid_sfe_polarity() -> None:
    disposition = escalate_disposition(
        proposed=Disposition.AUTO_CONTAIN,
        fault_flag=NEVER_CONTAIN_SNAPSHOT,
        system_fault=True,
    )
    with pytest.raises(
        InvalidDecisionEdictFaultFlagError, match="system_fault_escalation"
    ):
        build_decision_edict(
            attempt=_attempt(),
            judgment=skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN),
            disposition=disposition,
            live_never_contain_entries=[],
            stamp_status="not_required",
            ticket_stamp_payload={},
        )


def test_build_decision_edict_accepts_canonical_fault_flag_bundle() -> None:
    judgment = skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN)
    disposition = escalate_disposition(
        proposed=Disposition.AUTO_CONTAIN,
        fault_flag=OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value,
        system_fault=True,
    )
    edict = build_decision_edict(
        attempt=_attempt(),
        judgment=judgment,
        disposition=disposition,
        live_never_contain_entries=[],
        stamp_status="not_required",
        ticket_stamp_payload={},
    )
    assert edict.fault_flags == [OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value]
    assert edict.system_fault_escalation is True
