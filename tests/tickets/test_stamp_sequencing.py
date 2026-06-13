"""TASK-023 — Ticket stamp contract integration and sequencing."""

from __future__ import annotations

from typing import Any

import pytest
from tests.config.shared import EXAMPLE_SNAPSHOT_HASH
from tests.engine.helpers import assert_outcome_matrix_edict, fetch_ledger_edicts
from tests.engine.stamp_fakes import (
    AlwaysFailedStampBackend,
    ResolveUnknownOnRetryBackend,
)

from praetor.contracts.disposition import Disposition
from praetor.engine.edict import skeleton_policy_result
from praetor.engine.ids import stamp_evidence_hash
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.engine.recovery import recover_single_attempt, run_engine_startup_recovery
from praetor.engine.skeleton import (
    SKELETON_ALERT_ID,
    SKELETON_BUNDLE_HASH,
    skeleton_model_judgment,
)
from praetor.hashing import derive_stamp_id
from praetor.judgment.fake_provider import FakeProvider
from praetor.state.attempts import (
    ActiveAttemptExistsError,
    AttemptState,
    _fetch_attempt_by_id,
    transition_attempt,
)
from praetor.state.store import StateStore
from praetor.tickets.contract import (
    TICKET_STAMP_FAILED,
    StampContractDisposition,
    apply_terminal_stamp_to_disposition,
    candidate_judgment_from_stamp_payload,
    stamp_status_allows_edict_append,
)
from praetor.tickets.outbox import StampStatus, fetch_stamp_outbox
from praetor.tickets.stamp import (
    StampBackendOutcome,
    StampBackendResult,
    StampContext,
    StampTimeoutError,
    execute_stamp,
)


class UnreachableTicketBackend:
    """Definitive ticket-system rejection (not ambiguous timeout)."""

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        _ = stamp_id, payload
        return StampBackendResult(
            outcome=StampBackendOutcome.FAILED,
            payload={"error": "ticket_api_unreachable"},
        )


class AmbiguousThenFailedBackend:
    """First call ambiguous; retry resolves to failed (unreachable after retry)."""

    def __init__(self) -> None:
        self.stamp_calls: list[str] = []

    def stamp(self, stamp_id: str, payload: dict[str, Any]) -> StampBackendResult:
        self.stamp_calls.append(stamp_id)
        if len(self.stamp_calls) == 1:
            raise StampTimeoutError("connection lost")
        return StampBackendResult(outcome=StampBackendOutcome.FAILED, payload={})


def _pre_stamp_for(judgment_proposed: Disposition) -> StampContractDisposition:
    judgment = skeleton_model_judgment(proposed=judgment_proposed)
    disposition = skeleton_policy_result(judgment)
    if disposition.final_disposition == Disposition.AUTO_CONTAIN:
        return StampContractDisposition(
            final_disposition=Disposition.ESCALATE,
            fault_flags=[],
            system_fault_escalation=False,
            proposed_disposition=judgment_proposed,
        )
    return StampContractDisposition(
        final_disposition=disposition.final_disposition,
        fault_flags=list(disposition.fault_flags),
        system_fault_escalation=disposition.system_fault_escalation,
        proposed_disposition=disposition.proposed_disposition,
    )


@pytest.mark.parametrize(
    ("proposed", "expected_final"),
    [
        (Disposition.STANDARD_REVIEW, Disposition.STANDARD_REVIEW),
        (Disposition.ESCALATE, Disposition.ESCALATE),
        (Disposition.AUTO_CONTAIN, Disposition.ESCALATE),
    ],
)
def test_stamp_success_preserves_candidate_disposition(
    proposed: Disposition,
    expected_final: Disposition,
) -> None:
    pre = _pre_stamp_for(proposed)
    result = apply_terminal_stamp_to_disposition(
        StampStatus.SUCCEEDED,
        pre_stamp_disposition=pre,
    )
    assert result == pre
    assert result.final_disposition == expected_final
    assert result.fault_flags == []


def test_stamp_failure_preserves_standard_review() -> None:
    pre = _pre_stamp_for(Disposition.STANDARD_REVIEW)
    result = apply_terminal_stamp_to_disposition(
        StampStatus.FAILED,
        pre_stamp_disposition=pre,
    )
    assert_outcome_matrix_edict(
        _disposition_as_edict_fields(result),
        final_disposition=Disposition.STANDARD_REVIEW,
        fault_flags=[TICKET_STAMP_FAILED],
        system_fault_escalation=False,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )


def test_stamp_failure_preserves_escalate_candidate() -> None:
    pre = _pre_stamp_for(Disposition.ESCALATE)
    result = apply_terminal_stamp_to_disposition(
        StampStatus.FAILED,
        pre_stamp_disposition=pre,
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.proposed_disposition == Disposition.ESCALATE
    assert result.fault_flags == [TICKET_STAMP_FAILED]


def test_stamp_failure_appends_flag_preserving_existing_fault_flags() -> None:
    pre = StampContractDisposition(
        final_disposition=Disposition.ESCALATE,
        fault_flags=["never_contain_snapshot"],
        system_fault_escalation=False,
        proposed_disposition=Disposition.ESCALATE,
    )
    result = apply_terminal_stamp_to_disposition(
        StampStatus.FAILED,
        pre_stamp_disposition=pre,
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == ["never_contain_snapshot", TICKET_STAMP_FAILED]
    assert result.system_fault_escalation is False
    assert result.proposed_disposition == Disposition.ESCALATE


def test_stamp_failure_preserves_final_when_final_differs_from_proposed() -> None:
    pre = StampContractDisposition(
        final_disposition=Disposition.ESCALATE,
        fault_flags=["config_over_budget"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    result = apply_terminal_stamp_to_disposition(
        StampStatus.FAILED,
        pre_stamp_disposition=pre,
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.proposed_disposition == Disposition.STANDARD_REVIEW
    assert result.fault_flags == ["config_over_budget", TICKET_STAMP_FAILED]
    assert result.system_fault_escalation is True


@pytest.mark.parametrize(
    "status",
    [StampStatus.PENDING, StampStatus.UNKNOWN],
)
def test_apply_terminal_stamp_raises_for_non_terminal_status(
    status: StampStatus,
) -> None:
    pre = _pre_stamp_for(Disposition.STANDARD_REVIEW)
    with pytest.raises(ValueError, match="is not terminal for edict append"):
        apply_terminal_stamp_to_disposition(status, pre_stamp_disposition=pre)


def test_stamp_failure_preserves_autocontain_candidate() -> None:
    pre = _pre_stamp_for(Disposition.AUTO_CONTAIN)
    result = apply_terminal_stamp_to_disposition(
        StampStatus.FAILED,
        pre_stamp_disposition=pre,
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.proposed_disposition == Disposition.AUTO_CONTAIN
    assert result.fault_flags == [TICKET_STAMP_FAILED]
    assert result.system_fault_escalation is False


def test_stamp_status_allows_edict_append_only_for_terminal_outcomes() -> None:
    assert stamp_status_allows_edict_append(StampStatus.SUCCEEDED) is True
    assert stamp_status_allows_edict_append(StampStatus.FAILED) is True
    assert stamp_status_allows_edict_append(StampStatus.PENDING) is False
    assert stamp_status_allows_edict_append(StampStatus.UNKNOWN) is False


def test_no_ledger_edict_while_stamp_in_flight(activated: StateStore) -> None:
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-IN-FLIGHT",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)

    execute_stamp(
        activated.conn,
        AmbiguousThenFailedBackend(),
        StampContext(
            alert_identity=alloc.attempt.alert_identity,
            evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
            org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
            processing_attempt_identity=aid,
            ticket_payload={
                "candidate_judgment": skeleton_model_judgment().model_dump(mode="json"),
            },
        ),
    )

    assert fetch_ledger_edicts(activated.conn) == []
    row = activated.conn.execute(
        "SELECT state FROM processing_attempts WHERE attempt_id = ?",
        (int(aid),),
    ).fetchone()
    assert row is not None
    assert str(row["state"]) == AttemptState.PENDING_STAMP.value


def test_intake_stamp_failure_preserves_standard_review(activated: StateStore) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.STANDARD_REVIEW)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AlwaysFailedStampBackend(),
    )
    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.STANDARD_REVIEW,
        fault_flags=[TICKET_STAMP_FAILED],
        system_fault_escalation=False,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert result.edict.stamp_status == "failed"


def test_intake_stamp_failure_preserves_escalate_candidate(
    activated: StateStore,
) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.ESCALATE)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AlwaysFailedStampBackend(),
    )
    assert result.edict is not None
    assert result.edict.final_disposition == Disposition.ESCALATE
    assert result.edict.fault_flags == [TICKET_STAMP_FAILED]


def test_intake_stamp_success_preserves_candidate(activated: StateStore) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.STANDARD_REVIEW)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
    )
    assert result.edict is not None
    assert result.edict.final_disposition == Disposition.STANDARD_REVIEW
    assert result.edict.fault_flags == []
    assert result.edict.stamp_status == "succeeded"


def test_unreachable_ticket_system_treated_as_stamp_failure(
    activated: StateStore,
) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.STANDARD_REVIEW)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=UnreachableTicketBackend(),
    )
    assert result.edict is not None
    assert result.edict.stamp_status == "failed"
    assert TICKET_STAMP_FAILED in result.edict.fault_flags
    assert result.edict.final_disposition == Disposition.STANDARD_REVIEW


def test_redelivery_while_stamp_in_flight_raises_active_attempt_exists(
    activated: StateStore,
) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.STANDARD_REVIEW)
    process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AmbiguousThenFailedBackend(),
    )
    with pytest.raises(ActiveAttemptExistsError):
        process_alert_intake(
            activated,
            judgment_provider=provider,
            stamp_backend=AmbiguousThenFailedBackend(),
        )


def test_intake_defers_edict_on_ambiguous_stamp(activated: StateStore) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.STANDARD_REVIEW)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AmbiguousThenFailedBackend(),
    )
    assert result.edict is None
    assert result.decision_id is None
    assert result.attempt_aborted is False
    assert fetch_ledger_edicts(activated.conn) == []


def test_unknown_recovery_resends_same_stamp_id(activated: StateStore) -> None:
    provider = FakeProvider(proposed_disposition=Disposition.ESCALATE)
    process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AmbiguousThenFailedBackend(),
    )
    stamp_id = derive_stamp_id(
        SKELETON_ALERT_ID,
        stamp_evidence_hash(evidence_bundle_hash_value=SKELETON_BUNDLE_HASH),
        EXAMPLE_SNAPSHOT_HASH,
    )
    entry_before = fetch_stamp_outbox(activated.conn, stamp_id)
    assert entry_before is not None
    assert entry_before.status == StampStatus.UNKNOWN
    assert (
        entry_before.ticket_payload["candidate_judgment"]["proposed_disposition"]
        == Disposition.ESCALATE.value
    )

    backend = ResolveUnknownOnRetryBackend(resolve_to=StampBackendOutcome.SUCCEEDED)
    run_engine_startup_recovery(activated, stamp_backend=backend)

    assert len(backend.stamp_calls) == 2
    assert backend.stamp_calls[0] == backend.stamp_calls[1] == stamp_id
    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert edicts[0].stamp_status == "succeeded"
    assert edicts[0].final_disposition == Disposition.ESCALATE
    assert edicts[0].fault_flags == []


def test_candidate_judgment_from_stamp_payload_missing_uses_skeleton_default(
    activated: StateStore,
) -> None:
    assert candidate_judgment_from_stamp_payload({"ticket_ref": "no-candidate"}) is None

    alloc = activated.allocate_attempt(
        alert_identity="ALERT-NO-CANDIDATE",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    execute_stamp(
        activated.conn,
        AlwaysFailedStampBackend(),
        StampContext(
            alert_identity=alloc.attempt.alert_identity,
            evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
            org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
            processing_attempt_identity=aid,
            ticket_payload={"ticket_ref": "no-candidate"},
        ),
    )
    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)
    refreshed = _fetch_attempt_by_id(activated.conn, aid)
    assert refreshed is not None
    recover_single_attempt(activated, refreshed, AlwaysFailedStampBackend())
    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert (
        edicts[0].model_judgment.proposed_disposition
        == skeleton_model_judgment().proposed_disposition
    )


def _disposition_as_edict_fields(
    disposition: StampContractDisposition,
) -> object:
    """Minimal adapter so assert_outcome_matrix_edict can validate disposition rows."""

    class _Adapter:
        final_disposition = disposition.final_disposition
        fault_flags = disposition.fault_flags
        system_fault_escalation = disposition.system_fault_escalation

        @property
        def policy_gate_result(self) -> object:
            from praetor.contracts.policy import PolicyGateResult

            return PolicyGateResult(
                proposed_disposition=disposition.proposed_disposition,
                final_disposition=disposition.final_disposition,
            )

    return _Adapter()
