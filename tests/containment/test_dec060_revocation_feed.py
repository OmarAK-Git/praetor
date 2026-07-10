"""V2-018 — DEC-060 expiry, re-issue, and supersession feed semantics."""

from __future__ import annotations

from datetime import timedelta

import pytest
from tests.containment.conftest import NOW, sample_host_directive
from tests.ledger.conftest import sample_decision_edict

from praetor.config.directives import commit_outstanding_directive
from praetor.config.state import (
    fetch_expired_unrevoked_directives,
    fetch_outstanding_unrevoked_directives,
)
from praetor.containment.lifecycle import (
    directive_is_outstanding_by_expiry,
    validate_expired_reissue_carve_out,
)
from praetor.containment.revocation import (
    SupersessionNotApplicableError,
    revoke_supersession_in_transaction,
)
from praetor.contracts.containment import DirectiveStatus
from praetor.hashing import derive_idempotency_key
from praetor.ledger.store import append_ledger_record
from praetor.policy.state import reconcile_policy_state
from praetor.state.idempotency import fetch_active_idempotency_key
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import StateStore


def test_expired_unrevoked_rows_excluded_from_outstanding_fetch(
    activated: StateStore,
) -> None:
    issued = NOW - timedelta(hours=1)
    expired = sample_host_directive(status=DirectiveStatus.EMITTED).model_copy(
        update={
            "directive_id": "dir-expired-residue",
            "issued_at": issued,
            "expires_at": issued + timedelta(seconds=30),
        }
    )
    live = sample_host_directive(
        directive_id="dir-live",
        status=DirectiveStatus.EMITTED,
        issued_at=NOW,
    )
    commit_outstanding_directive(activated.conn, expired)
    commit_outstanding_directive(activated.conn, live)

    assert fetch_expired_unrevoked_directives(activated.conn, now=NOW) == [expired]
    outstanding = fetch_outstanding_unrevoked_directives(activated.conn, now=NOW)
    assert [d.directive_id for d in outstanding] == ["dir-live"]


def test_reconcile_skips_expired_unrevoked_idempotency(activated: StateStore) -> None:
    issued = NOW - timedelta(hours=1)
    alert_identity = "ALERT-EXPIRED-RESIDUE"
    idem_key = derive_idempotency_key(alert_identity, "host", "dc-01", "host-isolation")
    expired = sample_host_directive(status=DirectiveStatus.EMITTED).model_copy(
        update={
            "directive_id": "dir-expired-reconcile",
            "decision_id": "dec-expired-reconcile",
            "issued_at": issued,
            "expires_at": issued + timedelta(seconds=30),
            "idempotency_key": idem_key,
        }
    )
    edict = sample_decision_edict(decision_id="dec-expired-reconcile").model_copy(
        update={"alert_reference": alert_identity}
    )
    with critical_transaction(activated.conn):
        append_ledger_record(activated.conn, edict)
    commit_outstanding_directive(activated.conn, expired)
    activated.conn.commit()

    result = reconcile_policy_state(activated.conn)
    activated.conn.commit()

    assert result.idempotency_keys_registered == 0
    assert fetch_active_idempotency_key(activated.conn, idem_key) is None


def test_revoke_supersession_rejects_expired_directive(activated: StateStore) -> None:
    issued = NOW - timedelta(hours=1)
    expired = sample_host_directive(status=DirectiveStatus.EMITTED).model_copy(
        update={
            "directive_id": "dir-expired-super",
            "issued_at": issued,
            "expires_at": issued + timedelta(seconds=30),
        }
    )
    commit_outstanding_directive(activated.conn, expired)
    assert not directive_is_outstanding_by_expiry(expired, now=NOW)

    with pytest.raises(SupersessionNotApplicableError, match="still-live"):
        with critical_transaction(activated.conn):
            revoke_supersession_in_transaction(
                activated.conn,
                activated,
                expired,
                superseded_by_directive_id="dir-new",
                triggered_by="policy-gate",
                now=NOW,
            )


def test_validate_expired_reissue_carve_out_rejects_supersedes_link() -> None:
    replacement = sample_host_directive(status=DirectiveStatus.PROPOSED).model_copy(
        update={"supersedes_directive_id": "dir-old"}
    )
    with pytest.raises(ValueError, match="supersedes_directive_id"):
        validate_expired_reissue_carve_out(replacement)
