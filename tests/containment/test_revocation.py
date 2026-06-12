"""TASK-020 differentiated revocation trigger tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN
from tests.containment.conftest import NOW, sample_host_directive

from praetor.config.activation import activate_org_config
from praetor.config.directives import commit_outstanding_directive
from praetor.config.emergency import add_emergency_never_contain
from praetor.config.health_emit import drain_unflushed_health_alerts
from praetor.containment.revocation import (
    NEVER_CONTAIN_CONFLICT_ALERT,
    POST_ACTIVATION_CONFLICT_ALERT,
    automated_revoke_directive_in_transaction,
    manual_revoke_directive,
    new_revocation_record,
    revoke_directives_matching_never_contain,
    revoke_supersession_in_transaction,
)
from praetor.contracts.containment import DirectiveStatus
from praetor.contracts.ledger import RevocationReason
from praetor.engine.recovery import reconcile_outstanding_directives_never_contain
from praetor.hashing import derive_idempotency_key
from praetor.ledger.hash_chain import verify_ledger_chain
from praetor.ledger.store import fetch_ledger_rows
from praetor.state.idempotency import fetch_active_idempotency_key
from praetor.state.sqlite_guard import critical_transaction
from praetor.state.store import (
    StateStore,
    fetch_feed_outbox_row,
    fetch_revocation_record_json,
)


def _register_key(store: StateStore) -> str:
    key = derive_idempotency_key("ALERT-R", "host", "dc-01", "host-isolation")
    store.register_idempotency_key(
        idempotency_key=key,
        alert_identity="ALERT-R",
        target_type="host",
        target_id="dc-01",
        scope="host-isolation",
    )
    return key


def _count_alerts(conn, code: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (code,),
    ).fetchone()
    assert row is not None
    return int(row["c"])


def test_automated_revocation_writes_ledger_and_feed(activated: StateStore) -> None:
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    commit_outstanding_directive(activated.conn, directive)
    record = new_revocation_record(
        directive,
        reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
        triggered_by="test",
        idempotency_key_cleared=False,
        now=NOW,
    )
    with critical_transaction(activated.conn):
        result = automated_revoke_directive_in_transaction(
            activated.conn, activated, directive, record
        )
    assert result.sequence_number == 1
    stored_json = fetch_revocation_record_json(
        activated.conn, record.revocation_id
    )
    assert stored_json is not None
    assert fetch_feed_outbox_row(activated.conn, 1) is not None
    ledger = fetch_ledger_rows(activated.conn)
    assert len(ledger) == 1
    assert ledger[0].record_type == "directive_revocation"


def test_post_emission_conflict_emits_alert_keeps_key(activated: StateStore) -> None:
    key = _register_key(activated)
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    commit_outstanding_directive(activated.conn, directive)
    drain_unflushed_health_alerts(activated.conn)

    revoked, emitted = reconcile_outstanding_directives_never_contain(activated)
    assert directive.directive_id in revoked
    assert len(revoked) == 1
    assert len(emitted) == 1
    assert fetch_active_idempotency_key(activated.conn, key) is not None

    stored = fetch_revocation_record_json(
        activated.conn,
        fetch_feed_outbox_row(activated.conn, 1)["revocation_id"],  # type: ignore[index]
    )
    assert stored is not None
    payload = json.loads(stored)
    assert payload["reason"] == RevocationReason.NEVER_CONTAIN_CONFLICT.value
    assert _count_alerts(activated.conn, NEVER_CONTAIN_CONFLICT_ALERT) == 1


def test_manual_revocation_clears_key_in_one_tx(activated: StateStore) -> None:
    key = _register_key(activated)
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    commit_outstanding_directive(activated.conn, directive)
    result = manual_revoke_directive(
        activated,
        directive,
        idempotency_key=key,
        triggered_by="soc-lead-1",
        now=NOW,
    )
    assert fetch_active_idempotency_key(activated.conn, key) is None
    outbox = fetch_feed_outbox_row(activated.conn, result.sequence_number)
    assert outbox is not None
    stored = fetch_revocation_record_json(activated.conn, outbox["revocation_id"])
    assert stored is not None
    payload = json.loads(stored)
    assert payload["reason"] == RevocationReason.MANUAL.value
    assert payload["idempotency_key_cleared"] is True

    ledger = fetch_ledger_rows(activated.conn)
    assert len(ledger) == 1
    assert ledger[0].record_type == "directive_revocation"
    ledger_payload = json.loads(ledger[0].record_json)
    assert ledger_payload["revocation_id"] == result.record.revocation_id
    verify_ledger_chain(activated.conn)


def test_supersession_includes_superseded_by_keeps_key(activated: StateStore) -> None:
    key = _register_key(activated)
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    commit_outstanding_directive(activated.conn, directive)
    with critical_transaction(activated.conn):
        result = revoke_supersession_in_transaction(
            activated.conn,
            activated,
            directive,
            superseded_by_directive_id="dir-new",
            triggered_by="policy-gate",
            now=NOW,
        )
    stored = fetch_revocation_record_json(activated.conn, result.record.revocation_id)
    assert stored is not None
    payload = json.loads(stored)
    assert payload["reason"] == RevocationReason.SUPERSESSION.value
    assert payload["superseded_by_directive_id"] == "dir-new"
    assert payload["idempotency_key_cleared"] is False
    assert fetch_active_idempotency_key(activated.conn, key) is not None


def test_post_activation_reconciliation_revokes_and_alerts(
    store: StateStore, verifier
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    key = _register_key(store)
    directive = sample_host_directive(status=DirectiveStatus.EMITTED)
    commit_outstanding_directive(store.conn, directive)
    drain_unflushed_health_alerts(store.conn)

    activation = activate_org_config(
        store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
    )
    assert directive.directive_id in activation.revoked_directive_ids
    assert len(activation.revoked_directive_ids) == 1
    assert fetch_active_idempotency_key(store.conn, key) is not None

    stored = fetch_revocation_record_json(
        store.conn,
        fetch_feed_outbox_row(store.conn, 1)["revocation_id"],  # type: ignore[index]
    )
    assert stored is not None
    payload = json.loads(stored)
    assert payload["reason"] == RevocationReason.POST_ACTIVATION_RECONCILIATION.value
    assert (
        _count_alerts(store.conn, POST_ACTIVATION_CONFLICT_ALERT)
        == len(activation.revoked_directive_ids)
    )


def test_revoke_matching_skips_non_matching_targets(activated: StateStore) -> None:
    directive = sample_host_directive(
        directive_id="dir-other",
        target_id="ws-99",
        status=DirectiveStatus.EMITTED,
    )
    commit_outstanding_directive(activated.conn, directive)
    entries = [{"target_type": "host", "target_id": "dc-01"}]
    with critical_transaction(activated.conn):
        revoked = revoke_directives_matching_never_contain(
            activated.conn,
            activated,
            [directive],
            entries,
            reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
            triggered_by="test",
            now=NOW,
        )
    assert revoked == []


def test_expired_directive_not_revoked_on_reconciliation(
    store: StateStore, verifier
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    issued = datetime.now(UTC) - timedelta(hours=1)
    expired = sample_host_directive(status=DirectiveStatus.EMITTED).model_copy(
        update={
            "directive_id": "dir-expired",
            "issued_at": issued,
            "expires_at": issued + timedelta(seconds=30),
            "idempotency_key": "idem-exp",
        }
    )
    commit_outstanding_directive(store.conn, expired)
    activation = activate_org_config(
        store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
    )
    assert "dir-expired" not in activation.revoked_directive_ids


def test_emergency_conflict_revocation_rolls_back_on_injected_failure(
    activated: StateStore, verifier
) -> None:
    issued = datetime.now(UTC)
    directive = sample_host_directive(
        directive_id="dir-emerg-rollback",
        target_id="eng-99",
        status=DirectiveStatus.EMITTED,
    ).model_copy(
        update={
            "issued_at": issued,
            "expires_at": issued + timedelta(seconds=120),
        }
    )
    commit_outstanding_directive(activated.conn, directive)

    def boom() -> None:
        raise RuntimeError("injected failure")

    with pytest.raises(RuntimeError, match="injected failure"):
        add_emergency_never_contain(
            activated,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={"target_type": "host", "target_id": "eng-99"},
            lifetime_seconds=60,
            audit_reason="rollback-test",
            entry_id="enc-rollback-1",
            _test_before_conflict_revocation=boom,
        )

    assert fetch_active_emergency_records_count(activated) == 0
    assert fetch_revocation_record_count(activated) == 0
    assert fetch_feed_outbox_count(activated) == 0
    assert fetch_ledger_rows(activated.conn) == []


def fetch_active_emergency_records_count(store: StateStore) -> int:
    from praetor.config.state import fetch_active_emergency_records

    return len(fetch_active_emergency_records(store.conn))


def fetch_revocation_record_count(store: StateStore) -> int:
    row = store.conn.execute(
        "SELECT COUNT(*) AS c FROM directive_revocation_records"
    ).fetchone()
    assert row is not None
    return int(row["c"])


def fetch_feed_outbox_count(store: StateStore) -> int:
    row = store.conn.execute(
        "SELECT COUNT(*) AS c FROM revocation_feed_outbox"
    ).fetchone()
    assert row is not None
    return int(row["c"])
