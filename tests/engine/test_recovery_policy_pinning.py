"""V2-010 — recovery policy pinning (DEC-060)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.config.shared import EXAMPLE_SNAPSHOT_HASH
from tests.engine.helpers import assert_outcome_matrix_edict, fetch_ledger_edicts
from tests.engine.stamp_fakes import (
    AlwaysSucceededStampBackend,
)

from praetor.config.directives import commit_outstanding_directive
from praetor.containment.revocation import ORPHAN_OUTSTANDING_DIRECTIVE_ALERT
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.disposition import Disposition
from praetor.engine.recovery import (
    _recovery_disposition_for_stamp,
    run_engine_startup_recovery,
)
from praetor.engine.skeleton import SKELETON_BUNDLE_HASH, skeleton_model_judgment
from praetor.hashing import derive_idempotency_key
from praetor.policy.state import fetch_orphan_outstanding_directives
from praetor.state.attempts import AttemptState, transition_attempt
from praetor.state.store import open_state_store
from praetor.tickets.outbox import StampStatus
from praetor.tickets.stamp import StampContext, execute_stamp


def test_recovery_disposition_downgrades_autocontain_before_stamp_contract() -> None:
    """Pinned: recovery pre-stamp path never leaves auto_contain as final disposition."""
    judgment = skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN)
    for stamp_status in (StampStatus.SUCCEEDED, StampStatus.FAILED):
        disposition = _recovery_disposition_for_stamp(stamp_status, judgment)
        assert disposition.final_disposition == Disposition.ESCALATE
        assert disposition.proposed_disposition == Disposition.AUTO_CONTAIN
        assert disposition.system_fault_escalation is False


def test_successful_stamp_recovery_downgrades_autocontain_candidate(
    activated,
) -> None:
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-REC-AC-OK",
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
        AlwaysSucceededStampBackend(),
        StampContext(
            alert_identity=alloc.attempt.alert_identity,
            evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
            org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
            processing_attempt_identity=aid,
            ticket_payload={"candidate_judgment": judgment.model_dump(mode="json")},
        ),
    )
    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)

    run_engine_startup_recovery(
        activated, stamp_backend=AlwaysSucceededStampBackend()
    )

    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert_outcome_matrix_edict(
        edicts[0],
        final_disposition=Disposition.ESCALATE,
        fault_flags=[],
        system_fault_escalation=False,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )
    assert edicts[0].stamp_status == "succeeded"


def test_fetch_orphan_outstanding_directives_detects_missing_ledger_edict(
    activated,
) -> None:
    issued = datetime.now(UTC)
    orphan = ContainmentDirective(
        directive_id="dir-orphan-pin",
        decision_id="dec-no-ledger",
        target_type=TargetType.HOST,
        target_id="ws-orphan-pin",
        scope="host-isolation",
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key=derive_idempotency_key(
            "ALERT-ORPHAN-PIN", "host", "ws-orphan-pin", "host-isolation"
        ),
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    commit_outstanding_directive(activated.conn, orphan)
    activated.conn.commit()

    orphans = fetch_orphan_outstanding_directives(activated.conn)
    assert len(orphans) == 1
    assert orphans[0].directive_id == "dir-orphan-pin"


def test_orphan_directive_emits_health_alert_on_startup_recovery(
    activated,
) -> None:
    issued = datetime.now(UTC)
    orphan = ContainmentDirective(
        directive_id="dir-orphan-alert",
        decision_id="dec-orphan-alert",
        target_type=TargetType.HOST,
        target_id="ws-orphan-alert",
        scope="host-isolation",
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key=derive_idempotency_key(
            "ALERT-ORPHAN-ALERT", "host", "ws-orphan-alert", "host-isolation"
        ),
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    commit_outstanding_directive(activated.conn, orphan)
    activated.conn.commit()

    result = run_engine_startup_recovery(activated)

    assert len(result.orphan_directive_alert_ids) == 1
    row = activated.conn.execute(
        """
        SELECT COUNT(*) AS c FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (ORPHAN_OUTSTANDING_DIRECTIVE_ALERT,),
    ).fetchone()
    assert row is not None
    assert int(row["c"]) == 1


def test_orphan_health_alert_idempotent_on_second_startup_recovery(
    activated,
) -> None:
    issued = datetime.now(UTC)
    orphan = ContainmentDirective(
        directive_id="dir-orphan-idem",
        decision_id="dec-orphan-idem",
        target_type=TargetType.HOST,
        target_id="ws-orphan-idem",
        scope="host-isolation",
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key=derive_idempotency_key(
            "ALERT-ORPHAN-IDEM", "host", "ws-orphan-idem", "host-isolation"
        ),
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    commit_outstanding_directive(activated.conn, orphan)
    activated.conn.commit()

    first = run_engine_startup_recovery(activated)
    second = run_engine_startup_recovery(activated)

    assert len(first.orphan_directive_alert_ids) == 1
    assert second.orphan_directive_alert_ids == []
    row = activated.conn.execute(
        """
        SELECT COUNT(*) AS c FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (ORPHAN_OUTSTANDING_DIRECTIVE_ALERT,),
    ).fetchone()
    assert row is not None
    assert int(row["c"]) == 1


def test_open_state_store_surfaces_orphan_before_feed_recovery(
    activated,
) -> None:
    """Engine recovery (steps 4–7) including orphan surfacing runs before feed (step 8)."""
    issued = datetime.now(UTC)
    orphan = ContainmentDirective(
        directive_id="dir-orphan-reopen",
        decision_id="dec-orphan-reopen",
        target_type=TargetType.HOST,
        target_id="ws-orphan-reopen",
        scope="host-isolation",
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key=derive_idempotency_key(
            "ALERT-ORPHAN-REOPEN", "host", "ws-orphan-reopen", "host-isolation"
        ),
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    commit_outstanding_directive(activated.conn, orphan)
    db_path = activated.db_path
    activated.close()

    reopened = open_state_store(db_path)
    try:
        row = reopened.conn.execute(
            """
            SELECT COUNT(*) AS c FROM system_health_alert_outbox
            WHERE alert_code = ?
            """,
            (ORPHAN_OUTSTANDING_DIRECTIVE_ALERT,),
        ).fetchone()
        assert row is not None
        assert int(row["c"]) == 1
    finally:
        reopened.close()
