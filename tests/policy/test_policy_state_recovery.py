"""TASK-017 policy state startup reconciliation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.ledger.conftest import sample_decision_edict

from praetor.config.directives import commit_outstanding_directive
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.hashing import derive_idempotency_key
from praetor.ledger.store import append_ledger_record
from praetor.policy.state import (
    rate_limit_scope_key,
    read_rate_counter,
    reconcile_policy_state,
    set_rate_counter,
)
from praetor.state.idempotency import fetch_active_idempotency_key
from praetor.state.sqlite_guard import critical_transaction


def test_reconcile_policy_state_reregisters_idempotency_and_resets_rate_counters(
    activated,
) -> None:
    host_id = "ws-05"
    alert_identity = f"ALERT-REC-{host_id}"
    decision_id = f"dec-rec-{host_id}"
    scope = "host-isolation"
    target_type = "host"
    idempotency_key = derive_idempotency_key(
        alert_identity, target_type, host_id, scope
    )
    issued = datetime.now(UTC)
    directive = ContainmentDirective(
        directive_id="dir-rec-05",
        decision_id=decision_id,
        target_type=TargetType.HOST,
        target_id=host_id,
        scope=scope,
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key=idempotency_key,
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    edict = sample_decision_edict(decision_id=decision_id).model_copy(
        update={"alert_reference": alert_identity}
    )
    with critical_transaction(activated.conn):
        append_ledger_record(activated.conn, edict)
    commit_outstanding_directive(activated.conn, directive)
    assert fetch_active_idempotency_key(activated.conn, idempotency_key) is None

    scope_key = rate_limit_scope_key(
        "per_host", target_type=target_type, target_id=host_id
    )
    set_rate_counter(activated.conn, scope_key, 99)
    activated.conn.commit()

    result = reconcile_policy_state(activated.conn)
    activated.conn.commit()

    assert result.idempotency_keys_registered == 1
    active = fetch_active_idempotency_key(activated.conn, idempotency_key)
    assert active is not None
    assert active.idempotency_key == derive_idempotency_key(
        alert_identity, target_type, host_id, scope
    )
    assert read_rate_counter(activated.conn, scope_key) == 0


def test_reconcile_skips_idempotency_when_ledger_edict_missing(
    activated, org_snapshot
) -> None:
    """Orphan outstanding directives without a ledger edict are skipped.

    Post-crash, a directive row without a resolvable alert_reference cannot
    re-register its idempotency key. A subsequent evaluate_policy_gate call for
    the same alert-target-scope could emit a second directive unless the
    outstanding row is cleaned up elsewhere — flagged for operator/recovery
    hardening, not papered over here.
    """
    issued = datetime.now(UTC)
    idem_key = derive_idempotency_key(
        "ALERT-ORPHAN", "host", "ws-orphan", "host-isolation"
    )
    orphan = ContainmentDirective(
        directive_id="dir-orphan",
        decision_id="dec-missing-from-ledger",
        target_type=TargetType.HOST,
        target_id="ws-orphan",
        scope="host-isolation",
        evidence_refs=["ev-host-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key=idem_key,
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:placeholder",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=0,
    )
    commit_outstanding_directive(activated.conn, orphan)
    activated.conn.commit()

    reconcile_policy_state(activated.conn)
    activated.conn.commit()

    assert fetch_active_idempotency_key(activated.conn, idem_key) is None
