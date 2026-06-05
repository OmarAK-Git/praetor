"""TASK-012 startup recovery and crash reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tests.config.shared import EXAMPLE_SNAPSHOT_HASH
from tests.engine.helpers import (
    assert_edict_snapshot_pairing,
    assert_outcome_matrix_edict,
    count_ledger_records,
    count_stamp_outbox_rows,
    fetch_ledger_edicts,
)
from tests.engine.stamp_fakes import (
    AlwaysFailedStampBackend,
    AlwaysTimeoutStampBackend,
    ResolveUnknownOnRetryBackend,
)

from praetor.config.directives import commit_outstanding_directive
from praetor.config.state import read_live_never_contain_entries
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.disposition import Disposition
from praetor.contracts.ledger import EmergencyNeverContainRecord
from praetor.engine.edict import (
    append_edict_and_snapshot,
    build_decision_edict,
    skeleton_policy_result,
)
from praetor.engine.ids import stamp_evidence_hash
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.engine.recovery import run_engine_startup_recovery
from praetor.engine.skeleton import SKELETON_BUNDLE_HASH, skeleton_model_judgment
from praetor.hashing import EMPTY_BUNDLE, derive_stamp_id
from praetor.revocation.exporter import default_feed_jsonl_path
from praetor.revocation.outbox import FeedOutboxStatus
from praetor.state.attempts import (
    AttemptState,
    fetch_all_non_terminal_attempts,
    transition_attempt,
)
from praetor.state.store import open_state_store
from praetor.tickets.outbox import StampStatus, fetch_stamp_outbox
from praetor.tickets.stamp import StampBackendOutcome, StampContext, execute_stamp


def _directive_for_dc01() -> ContainmentDirective:
    issued = datetime.now(UTC)
    return ContainmentDirective(
        directive_id="dir-dc01",
        decision_id="dec-prior",
        target_type=TargetType.HOST,
        target_id="dc-01",
        scope="host-isolation",
        evidence_refs=["ev-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-dc01",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )


@pytest.mark.parametrize(
    "stop_state",
    [
        AttemptState.ALLOCATED,
        AttemptState.ACTIVE,
        AttemptState.PENDING_STAMP,
        AttemptState.STAMP_RESOLVED,
        AttemptState.READY_TO_APPEND,
    ],
)
def test_crash_at_lifecycle_state_recovery_never_autocontains(
    activated,
    stop_state: AttemptState,
) -> None:
    alloc = activated.allocate_attempt(
        alert_identity=f"ALERT-CRASH-{stop_state.value}",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    backend = SucceedingStampBackend()

    if stop_state != AttemptState.ALLOCATED:
        transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    if stop_state in (
        AttemptState.PENDING_STAMP,
        AttemptState.STAMP_RESOLVED,
        AttemptState.READY_TO_APPEND,
    ):
        transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
        execute_stamp(
            activated.conn,
            backend,
            StampContext(
                alert_identity=alloc.attempt.alert_identity,
                evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
                org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
                processing_attempt_identity=aid,
                ticket_payload={
                    "candidate_judgment": skeleton_model_judgment(
                        proposed=Disposition.AUTO_CONTAIN,
                    ).model_dump(mode="json"),
                },
            ),
        )
    if stop_state in (AttemptState.STAMP_RESOLVED, AttemptState.READY_TO_APPEND):
        transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)
    if stop_state == AttemptState.READY_TO_APPEND:
        transition_attempt(activated.conn, aid, AttemptState.READY_TO_APPEND)

    assert fetch_all_non_terminal_attempts(activated.conn)

    run_engine_startup_recovery(activated, stamp_backend=backend)

    for edict in fetch_ledger_edicts(activated.conn):
        assert edict.final_disposition != Disposition.AUTO_CONTAIN
        assert_edict_snapshot_pairing(activated.conn, edict)

    if stop_state in (AttemptState.ALLOCATED, AttemptState.ACTIVE):
        remaining = fetch_all_non_terminal_attempts(activated.conn)
        assert all(a.state == AttemptState.ABORTED for a in remaining) or not remaining


def test_startup_scans_outstanding_directives_against_never_contain(
    activated,
) -> None:
    commit_outstanding_directive(activated.conn, _directive_for_dc01())
    result = run_engine_startup_recovery(activated)
    assert "dir-dc01" in result.revoked_directive_ids
    row = activated.conn.execute(
        "SELECT revoked FROM outstanding_containment_directives WHERE directive_id = ?",
        ("dir-dc01",),
    ).fetchone()
    assert row is not None
    assert int(row["revoked"]) == 1
    assert count_ledger_records(activated.conn, "directive_revocation") == 1
    row = activated.conn.execute(
        """
        SELECT COUNT(*) AS c FROM system_health_alert_outbox
        WHERE alert_code = 'never_contain_conflict'
        """
    ).fetchone()
    assert row is not None
    assert int(row["c"]) == 1


def test_startup_directive_scan_is_idempotent(activated) -> None:
    commit_outstanding_directive(activated.conn, _directive_for_dc01())
    first = run_engine_startup_recovery(activated)
    second = run_engine_startup_recovery(activated)
    assert first.revoked_directive_ids == ["dir-dc01"]
    assert second.revoked_directive_ids == []
    # Returned alert ids reflect only this scan's conflict alerts.
    assert len(first.emitted_health_alert_ids) == 1
    assert second.emitted_health_alert_ids == []
    assert count_ledger_records(activated.conn, "directive_revocation") == 1
    row = activated.conn.execute(
        "SELECT COUNT(*) AS c FROM revocation_feed_outbox"
    ).fetchone()
    assert row is not None
    assert int(row["c"]) == 1
    row = activated.conn.execute(
        """
        SELECT COUNT(*) AS c FROM system_health_alert_outbox
        WHERE alert_code = 'never_contain_conflict'
        """
    ).fetchone()
    assert row is not None
    assert int(row["c"]) == 1


def test_reopen_store_exports_feed_after_directive_reconciliation(
    activated,
    tmp_path: Path,
) -> None:
    """Feed recovery (step 8) runs after engine recovery (step 7) on reopen."""
    commit_outstanding_directive(activated.conn, _directive_for_dc01())
    db_path = activated.db_path
    activated.close()

    reopened = open_state_store(db_path)
    try:
        feed_path = default_feed_jsonl_path(db_path)
        assert feed_path.exists()
        text = feed_path.read_text(encoding="utf-8")
        assert "dir-dc01" in text
        row = reopened.conn.execute(
            """
            SELECT status FROM revocation_feed_outbox
            WHERE directive_id = 'dir-dc01'
            """
        ).fetchone()
        assert row is not None
        assert str(row["status"]) == FeedOutboxStatus.EXPORTED.value
    finally:
        reopened.close()


def test_emergency_record_write_is_all_or_nothing(activated) -> None:
    from praetor.config.state import (
        fetch_active_emergency_records,
        insert_emergency_record,
    )
    from praetor.state.sqlite_guard import critical_transaction

    before = len(fetch_active_emergency_records(activated.conn))
    record = EmergencyNeverContainRecord(
        entry_id="enc-crash-test",
        target_specification={"target_type": "host", "target_id": "host-x"},
        added_by="soc-lead-1",
        added_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        audit_reason="test",
    )
    try:
        with critical_transaction(activated.conn):
            insert_emergency_record(activated.conn, record)
            raise RuntimeError("simulated crash before commit")
    except RuntimeError:
        pass
    assert len(fetch_active_emergency_records(activated.conn)) == before

    with critical_transaction(activated.conn):
        insert_emergency_record(activated.conn, record)
    assert any(
        r.entry_id == "enc-crash-test"
        for r in fetch_active_emergency_records(activated.conn)
    )


def test_reopen_store_runs_engine_recovery(activated) -> None:
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-REOPEN",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    transition_attempt(
        activated.conn,
        alloc.attempt.processing_attempt_identity,
        AttemptState.ACTIVE,
    )
    path = activated.db_path
    activated.close()

    reopened = open_state_store(path)
    try:
        remaining = fetch_all_non_terminal_attempts(reopened.conn)
        assert remaining == [] or all(
            a.state == AttemptState.ABORTED for a in remaining
        )
    finally:
        reopened.close()


@pytest.mark.parametrize("stop_state", [AttemptState.STAMP_RESOLVED, AttemptState.READY_TO_APPEND])
def test_unknown_stamp_recovery_at_stamp_resolved_states(
    activated,
    stop_state: AttemptState,
) -> None:
    alloc = activated.allocate_attempt(
        alert_identity=f"ALERT-UNK-{stop_state.value}",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    backend = ResolveUnknownOnRetryBackend(resolve_to=StampBackendOutcome.SUCCEEDED)
    execute_stamp(
        activated.conn,
        backend,
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
    stamp_id = derive_stamp_id(
        alloc.attempt.alert_identity,
        stamp_evidence_hash(
            evidence_bundle_hash_value=alloc.attempt.evidence_bundle_hash
        ),
        alloc.attempt.org_config_snapshot_hash,
    )
    entry = fetch_stamp_outbox(activated.conn, stamp_id)
    assert entry is not None
    assert entry.status == StampStatus.UNKNOWN
    assert len(backend.stamp_calls) == 1
    stamp_rows_before = count_stamp_outbox_rows(activated.conn)

    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)
    if stop_state == AttemptState.READY_TO_APPEND:
        transition_attempt(activated.conn, aid, AttemptState.READY_TO_APPEND)

    run_engine_startup_recovery(activated, stamp_backend=backend)

    assert count_stamp_outbox_rows(activated.conn) == stamp_rows_before
    assert len(backend.stamp_calls) == 2
    assert backend.stamp_calls[0] == backend.stamp_calls[1]
    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert edicts[0].stamp_status == "succeeded"
    assert "ticket_stamp_unknown" not in edicts[0].fault_flags
    assert_edict_snapshot_pairing(activated.conn, edicts[0])


def test_failed_stamp_recovery_preserves_standard_review(activated) -> None:
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-STAMP-FAIL",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    judgment = skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)
    execute_stamp(
        activated.conn,
        AlwaysFailedStampBackend(),
        StampContext(
            alert_identity=alloc.attempt.alert_identity,
            evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
            org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
            processing_attempt_identity=aid,
            ticket_payload={"candidate_judgment": judgment.model_dump(mode="json")},
        ),
    )
    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)

    run_engine_startup_recovery(activated, stamp_backend=AlwaysFailedStampBackend())

    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert_outcome_matrix_edict(
        edicts[0],
        final_disposition=Disposition.STANDARD_REVIEW,
        fault_flags=["ticket_stamp_failed"],
        system_fault_escalation=False,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert edicts[0].stamp_status == "failed"
    assert_edict_snapshot_pairing(activated.conn, edicts[0])


def test_recovered_intake_reuses_completed_decision_without_duplicates(
    activated,
    judgment_provider,
    stamp_backend,
) -> None:
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-DEDUP",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    execute_stamp(
        activated.conn,
        stamp_backend,
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
    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)

    run_engine_startup_recovery(activated, stamp_backend=stamp_backend)
    first_edict_count = count_ledger_records(activated.conn, "decision_edict")
    first_snapshot_count = count_ledger_records(
        activated.conn, "never_contain_snapshot"
    )

    again = process_alert_intake(
        activated,
        judgment_provider=judgment_provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-DEDUP",
    )
    assert again.edict is None
    assert again.decision_id is not None
    assert count_ledger_records(activated.conn, "decision_edict") == first_edict_count
    assert (
        count_ledger_records(activated.conn, "never_contain_snapshot")
        == first_snapshot_count
    )


def test_crash_window_edict_appended_attempt_not_completed_does_not_duplicate(
    activated,
) -> None:
    """Spec step 5: crash between ledger append and attempt completion.

    The edict (+ snapshot) is already on the ledger but the attempt is still
    non-terminal. Recovery must finalize the attempt and must NOT append a
    second edict (ledger_has_edict_for_decision_id True branch).
    """
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-CRASH-WINDOW",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    for state in (
        AttemptState.ACTIVE,
        AttemptState.PENDING_STAMP,
        AttemptState.STAMP_RESOLVED,
        AttemptState.READY_TO_APPEND,
    ):
        attempt = transition_attempt(activated.conn, aid, state)

    judgment = skeleton_model_judgment()
    never_contain = read_live_never_contain_entries(activated.conn)
    edict = build_decision_edict(
        attempt=attempt,
        judgment=judgment,
        disposition=skeleton_policy_result(judgment),
        live_never_contain_entries=never_contain,
        stamp_status="succeeded",
        ticket_stamp_payload={"candidate_judgment": judgment.model_dump(mode="json")},
    )
    # Append ledger records but deliberately leave the attempt in ready_to_append.
    append_edict_and_snapshot(
        activated.conn, edict=edict, never_contain_entries=never_contain
    )
    assert count_ledger_records(activated.conn, "decision_edict") == 1
    assert count_ledger_records(activated.conn, "never_contain_snapshot") == 1
    assert fetch_all_non_terminal_attempts(activated.conn)

    run_engine_startup_recovery(activated)

    # No duplicate edict/snapshot; attempt finalized; completed-decision row exists.
    assert count_ledger_records(activated.conn, "decision_edict") == 1
    assert count_ledger_records(activated.conn, "never_contain_snapshot") == 1
    assert fetch_all_non_terminal_attempts(activated.conn) == []
    completed = activated.conn.execute(
        "SELECT decision_id FROM completed_decisions WHERE alert_identity = ?",
        ("ALERT-CRASH-WINDOW",),
    ).fetchall()
    assert len(completed) == 1
    assert str(completed[0]["decision_id"]) == edict.decision_id


def test_unresolvable_unknown_stamp_aborts_attempt_without_edict(activated) -> None:
    """Spec §147: a stamp that never resolves (persistent ambiguity) aborts; no edict."""
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-UNK-ABORT",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    backend = AlwaysTimeoutStampBackend()
    # Create the initial UNKNOWN outbox row.
    execute_stamp(
        activated.conn,
        backend,
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
    stamp_id = derive_stamp_id(
        alloc.attempt.alert_identity,
        stamp_evidence_hash(
            evidence_bundle_hash_value=alloc.attempt.evidence_bundle_hash
        ),
        alloc.attempt.org_config_snapshot_hash,
    )
    entry = fetch_stamp_outbox(activated.conn, stamp_id)
    assert entry is not None
    assert entry.status == StampStatus.UNKNOWN

    run_engine_startup_recovery(activated, stamp_backend=backend)

    # Resend attempted during recovery, still unknown -> attempt aborted, no edict.
    assert len(backend.stamp_calls) >= 2
    assert count_ledger_records(activated.conn, "decision_edict") == 0
    remaining = fetch_all_non_terminal_attempts(activated.conn)
    assert remaining == []
    aborted = activated.conn.execute(
        "SELECT state FROM processing_attempts WHERE attempt_id = ?",
        (int(aid),),
    ).fetchone()
    assert aborted is not None
    assert str(aborted["state"]) == AttemptState.ABORTED.value


def test_failed_stamp_with_autocontain_candidate_downgrades_to_escalate(
    activated,
) -> None:
    """Pinned interaction: ticket_stamp_failed normally preserves the candidate, but
    recovery never emits containment, so an auto_contain candidate is downgraded to
    escalate while retaining fault_flags=['ticket_stamp_failed'] and system_fault=False.
    """
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-FAIL-AC",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    judgment = skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN)
    execute_stamp(
        activated.conn,
        AlwaysFailedStampBackend(),
        StampContext(
            alert_identity=alloc.attempt.alert_identity,
            evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
            org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
            processing_attempt_identity=aid,
            ticket_payload={"candidate_judgment": judgment.model_dump(mode="json")},
        ),
    )
    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)

    run_engine_startup_recovery(activated, stamp_backend=AlwaysFailedStampBackend())

    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert_outcome_matrix_edict(
        edicts[0],
        final_disposition=Disposition.ESCALATE,
        fault_flags=["ticket_stamp_failed"],
        system_fault_escalation=False,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )
    assert edicts[0].final_disposition != Disposition.AUTO_CONTAIN
    assert edicts[0].stamp_status == "failed"
    assert_edict_snapshot_pairing(activated.conn, edicts[0])


def test_correlation_failure_redelivery_produces_second_edict(
    activated,
    judgment_provider,
    stamp_backend,
) -> None:
    """Pinned behavior: correlation failure aborts without a completed-decision row,
    so a redelivered correlation-failing alert allocates a fresh attempt and appends
    a second EMPTY_BUNDLE escalate edict. (Correlation may succeed on a later attempt.)
    """
    first = process_alert_intake(
        activated,
        judgment_provider=judgment_provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-CORR-REDELIVER",
        correlate=False,
    )
    second = process_alert_intake(
        activated,
        judgment_provider=judgment_provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-CORR-REDELIVER",
        correlate=False,
    )
    assert first.attempt_aborted is True
    assert second.attempt_aborted is True
    assert first.edict is not None and second.edict is not None
    assert first.edict.evidence_bundle_hash == EMPTY_BUNDLE
    assert second.edict.evidence_bundle_hash == EMPTY_BUNDLE
    # Distinct attempts -> distinct decision_ids -> two edicts on the ledger.
    assert first.edict.decision_id != second.edict.decision_id
    assert count_ledger_records(activated.conn, "decision_edict") == 2
    # No completed-decision dedup row is written on the abort path.
    completed = activated.conn.execute(
        "SELECT COUNT(*) AS c FROM completed_decisions WHERE alert_identity = ?",
        ("ALERT-CORR-REDELIVER",),
    ).fetchone()
    assert completed is not None
    assert int(completed["c"]) == 0
