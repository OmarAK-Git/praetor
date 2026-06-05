"""TASK-012 EMPTY_BUNDLE single-substitution-site invariant (docs/contracts.md §3.3)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from praetor.engine.edict import build_decision_edict, skeleton_policy_result
from praetor.engine.skeleton import SKELETON_BUNDLE_HASH, skeleton_model_judgment
from praetor.hashing import EMPTY_BUNDLE, derive_decision_id
from praetor.state.attempts import AttemptState, ProcessingAttempt


def _attempt() -> ProcessingAttempt:
    now = datetime.now(UTC)
    return ProcessingAttempt(
        processing_attempt_identity="7",
        alert_identity="ALERT-IDS",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash="snap-hash",
        state=AttemptState.STAMP_RESOLVED,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize("correlation_failure", [False, True])
def test_stored_bundle_hash_equals_decision_id_input(correlation_failure: bool) -> None:
    """The stored evidence_bundle_hash must be the exact value that fed decision_id."""
    attempt = _attempt()
    judgment = skeleton_model_judgment()
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=skeleton_policy_result(judgment),
        live_never_contain_entries=[],
        stamp_status="succeeded",
        ticket_stamp_payload={},
        correlation_failure=correlation_failure,
    )
    recomputed = derive_decision_id(
        attempt.alert_identity,
        edict.evidence_bundle_hash,
        attempt.org_config_snapshot_hash,
        attempt.processing_attempt_identity,
    )
    assert edict.decision_id == recomputed
    if correlation_failure:
        assert edict.evidence_bundle_hash == EMPTY_BUNDLE
    else:
        assert edict.evidence_bundle_hash == SKELETON_BUNDLE_HASH
