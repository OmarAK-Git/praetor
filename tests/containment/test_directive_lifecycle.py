"""TASK-020 directive lifecycle tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from tests.containment.conftest import NOW, sample_host_directive
from tests.policy.conftest import auto_contain_judgment, host_bundle

from praetor.containment.lifecycle import (
    build_proposed_directive_in_transaction,
    commit_outstanding_directive,
    emit_directive,
    insert_outstanding_directive_in_transaction,
    verify_consumer_embedded_hash,
)
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.hashing import compute_never_contain_entries_hash
from praetor.policy.containment_policy import ContainmentTarget
from praetor.policy.gate import evaluate_policy_gate
from praetor.revocation.outbox import mark_feed_row_exported
from praetor.state.sqlite_guard import critical_transaction


def test_status_transitions_proposed_to_emitted() -> None:
    proposed = sample_host_directive(status=DirectiveStatus.PROPOSED)
    emitted = emit_directive(proposed)
    assert emitted.status == DirectiveStatus.EMITTED
    assert emitted.directive_id == proposed.directive_id


def test_emit_is_idempotent_for_already_emitted() -> None:
    emitted = sample_host_directive(status=DirectiveStatus.EMITTED)
    assert emit_directive(emitted) is emitted


def test_directive_lifetime_capped_at_300_seconds() -> None:
    issued = NOW
    with pytest.raises(ValueError, match="300 seconds"):
        ContainmentDirective(
            directive_id="dir-long",
            decision_id="dec-1",
            target_type=TargetType.HOST,
            target_id="h1",
            scope="host-isolation",
            evidence_refs=[],
            issued_at=issued,
            expires_at=issued + timedelta(seconds=301),
            idempotency_key="k",
            actuator_constraints={},
            revocation_policy={},
            status=DirectiveStatus.PROPOSED,
            live_never_contain_hash="x",
            embedded_never_contain_entries=[],
            minimum_feed_sequence_at_issue=0,
        )


def test_account_target_id_must_be_sid() -> None:
    issued = NOW
    with pytest.raises(ValueError, match="SID"):
        ContainmentDirective(
            directive_id="dir-acct",
            decision_id="dec-1",
            target_type=TargetType.ACCOUNT,
            target_id="CORP\\jdoe",
            scope="account-isolation",
            evidence_refs=[],
            issued_at=issued,
            expires_at=issued + timedelta(seconds=60),
            idempotency_key="k",
            actuator_constraints={},
            revocation_policy={},
            status=DirectiveStatus.PROPOSED,
            live_never_contain_hash="x",
            embedded_never_contain_entries=[],
            minimum_feed_sequence_at_issue=0,
        )


def test_embedded_hash_matches_live_never_contain_hash(
    activated, org_snapshot
) -> None:
    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    with critical_transaction(activated.conn):
        directive = build_proposed_directive_in_transaction(
            activated.conn,
            decision_id="dec-hash",
            alert_identity="ALERT-HASH",
            target=target,
            evidence_refs=["ev-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=[],
            now=NOW,
        )
    assert verify_consumer_embedded_hash(directive)
    assert (
        compute_never_contain_entries_hash(directive.embedded_never_contain_entries)
        == directive.live_never_contain_hash
    )


def test_minimum_feed_sequence_fresh_db_is_zero(activated, org_snapshot) -> None:
    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    with critical_transaction(activated.conn):
        directive = build_proposed_directive_in_transaction(
            activated.conn,
            decision_id="dec-fresh",
            alert_identity="ALERT-FRESH",
            target=target,
            evidence_refs=["ev-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=[],
            now=NOW,
        )
    assert directive.minimum_feed_sequence_at_issue == 0


def test_minimum_feed_sequence_uses_verified_export(
    activated, org_snapshot
) -> None:
    with critical_transaction(activated.conn):
        activated.conn.execute(
            """
            INSERT INTO directive_revocation_records (
                revocation_id, directive_id, record_json, ledger_commit_at
            ) VALUES ('rev-seq', 'dir-seq', '{}', ?)
            """,
            (NOW.isoformat(),),
        )
        activated.conn.execute(
            """
            INSERT INTO revocation_feed_outbox (
                sequence_number, revocation_id, directive_id, status, created_at
            ) VALUES (1, 'rev-seq', 'dir-seq', 'pending', ?)
            """,
            (NOW.isoformat(),),
        )
        mark_feed_row_exported(activated.conn, sequence_number=1)

    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    with critical_transaction(activated.conn):
        directive = build_proposed_directive_in_transaction(
            activated.conn,
            decision_id="dec-seq",
            alert_identity="ALERT-SEQ",
            target=target,
            evidence_refs=["ev-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=[],
            now=NOW,
        )
    assert directive.minimum_feed_sequence_at_issue == 1


def test_minimum_feed_sequence_excludes_pending_unexported(
    activated, org_snapshot
) -> None:
    with critical_transaction(activated.conn):
        activated.conn.execute(
            """
            INSERT INTO directive_revocation_records (
                revocation_id, directive_id, record_json, ledger_commit_at
            ) VALUES ('rev-exp', 'dir-exp', '{}', ?)
            """,
            (NOW.isoformat(),),
        )
        activated.conn.execute(
            """
            INSERT INTO revocation_feed_outbox (
                sequence_number, revocation_id, directive_id, status, created_at
            ) VALUES (1, 'rev-exp', 'dir-exp', 'pending', ?)
            """,
            (NOW.isoformat(),),
        )
        mark_feed_row_exported(activated.conn, sequence_number=1)
        activated.conn.execute(
            """
            INSERT INTO directive_revocation_records (
                revocation_id, directive_id, record_json, ledger_commit_at
            ) VALUES ('rev-pend', 'dir-pend', '{}', ?)
            """,
            (NOW.isoformat(),),
        )
        activated.conn.execute(
            """
            INSERT INTO revocation_feed_outbox (
                sequence_number, revocation_id, directive_id, status, created_at
            ) VALUES (2, 'rev-pend', 'dir-pend', 'pending', ?)
            """,
            (NOW.isoformat(),),
        )

    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    with critical_transaction(activated.conn):
        directive = build_proposed_directive_in_transaction(
            activated.conn,
            decision_id="dec-mid-export",
            alert_identity="ALERT-MID",
            target=target,
            evidence_refs=["ev-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=[],
            now=NOW,
        )
    assert directive.minimum_feed_sequence_at_issue == 1


def test_consumer_verifies_embedded_hash(activated, org_snapshot) -> None:
    bundle = host_bundle(host_id="ws-01")
    result = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(bundle),
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity="ALERT-CONSUMER",
        decision_id="dec-consumer",
        now=NOW,
    )
    assert result.containment_directive is not None
    directive = result.containment_directive
    assert directive.status == DirectiveStatus.EMITTED
    assert verify_consumer_embedded_hash(directive)


def test_verify_consumer_embedded_hash_false_when_entries_mutated() -> None:
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    assert verify_consumer_embedded_hash(directive)
    tampered = directive.model_copy(
        update={
            "embedded_never_contain_entries": [
                {"target_type": "host", "target_id": "tampered"}
            ]
        }
    )
    assert not verify_consumer_embedded_hash(tampered)


def test_verify_consumer_embedded_hash_false_when_hash_replaced() -> None:
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    assert verify_consumer_embedded_hash(directive)
    tampered = directive.model_copy(update={"live_never_contain_hash": "sha256:bad"})
    assert not verify_consumer_embedded_hash(tampered)


def test_non_empty_embedded_subset_build_verify_round_trip(
    activated, org_snapshot
) -> None:
    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    live_entries: list[dict[str, object]] = [
        {"target_type": "host", "target_id": "ws-01", "source": "emergency"},
        {"target_type": "host", "target_id": "dc-01"},
    ]
    with critical_transaction(activated.conn):
        directive = build_proposed_directive_in_transaction(
            activated.conn,
            decision_id="dec-nonempty",
            alert_identity="ALERT-NONEMPTY",
            target=target,
            evidence_refs=["ev-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=live_entries,
            now=NOW,
        )
    assert len(directive.embedded_never_contain_entries) == 1
    assert directive.embedded_never_contain_entries[0]["target_id"] == "ws-01"
    assert verify_consumer_embedded_hash(directive)


def test_build_requires_critical_transaction(activated, org_snapshot) -> None:
    target = ContainmentTarget(
        target_type="host",
        target_id="ws-01",
        scope="host-isolation",
    )
    with pytest.raises(Exception, match="critical_transaction"):
        build_proposed_directive_in_transaction(
            activated.conn,
            decision_id="dec-tx",
            alert_identity="ALERT-TX",
            target=target,
            evidence_refs=["ev-1"],
            org_snapshot=org_snapshot,
            live_never_contain_entries=[],
            now=NOW,
        )


def test_persisted_directive_stored_as_emitted(activated) -> None:
    proposed = sample_host_directive(status=DirectiveStatus.PROPOSED)
    stored = commit_outstanding_directive(activated.conn, proposed)
    assert stored.status == DirectiveStatus.EMITTED
    row = activated.conn.execute(
        """
        SELECT directive_json FROM outstanding_containment_directives
        WHERE directive_id = ?
        """,
        (proposed.directive_id,),
    ).fetchone()
    assert row is not None
    persisted = ContainmentDirective.model_validate_json(str(row["directive_json"]))
    assert persisted.status == DirectiveStatus.EMITTED


def test_insert_outstanding_requires_critical_transaction(activated) -> None:
    proposed = sample_host_directive()
    with pytest.raises(Exception, match="critical_transaction"):
        insert_outstanding_directive_in_transaction(activated.conn, proposed)
