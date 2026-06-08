"""Task 9 — org config activation and reconciliation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from tests.config.helpers import preflight_path
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN

from praetor.auth import InsufficientRoleError, MissingTokenError
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.directives import commit_outstanding_directive
from praetor.config.state import fetch_active_org_config, fetch_snapshot_by_hash
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.ledger import RevocationReason
from praetor.ledger.store import fetch_ledger_rows
from praetor.state.attempts import allocate_attempt
from praetor.state.sqlite_guard import StartupGuardError
from praetor.state.store import (
    StateStore,
    fetch_feed_outbox_row,
    read_feed_sequence_next,
)


def test_activation_binds_snapshot_and_persists_immutable_copy(
    store: StateStore, verifier: PrincipalMapVerifier
) -> None:
    result = activate_org_config(
        store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
    )
    active = fetch_active_org_config(store.conn)
    assert active is not None
    assert active.snapshot_hash == result.snapshot_hash
    bound = fetch_snapshot_by_hash(store.conn, result.snapshot_hash)
    assert bound is not None
    assert bound.snapshot_hash == result.snapshot_hash


def test_in_flight_attempt_retrieves_snapshot_content_after_reactivation(
    store: StateStore, verifier: PrincipalMapVerifier, tmp_path: Path
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    first = preflight_path(EXAMPLE_CONFIG)
    result = allocate_attempt(
        store.conn,
        alert_identity="ALERT-KEEP-SNAPSHOT",
        evidence_bundle_hash="bundle-a",
        org_config_snapshot_hash=first.snapshot_hash,
    )
    assert result.attempt is not None
    original_hash = result.attempt.org_config_snapshot_hash

    updated = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    updated["business_context"]["notes"] = "changed for activation test"
    new_path = tmp_path / "updated_org.yaml"
    new_path.write_text(yaml.dump(updated), encoding="utf-8")
    activate_org_config(store, new_path, token=SOC_LEAD_TOKEN, verifier=verifier)

    retained = fetch_snapshot_by_hash(store.conn, original_hash)
    assert retained is not None
    assert retained.business_context.notes != "changed for activation test"

    row = store.conn.execute(
        """
        SELECT org_config_snapshot_hash FROM processing_attempts
        WHERE alert_identity = ?
        """,
        ("ALERT-KEEP-SNAPSHOT",),
    ).fetchone()
    assert row is not None
    assert str(row["org_config_snapshot_hash"]) == original_hash


def test_post_activation_reconciliation_writes_feed_outbox_and_keeps_idempotency(
    store: StateStore, verifier: PrincipalMapVerifier
) -> None:
    issued = datetime.now(UTC)
    directive = ContainmentDirective(
        directive_id="dir-reconcile-1",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="dc-01",
        scope="host-isolation",
        evidence_refs=["ev-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-reconcile-1",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:nc:abc",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )
    store.register_idempotency_key(
        idempotency_key="idem-reconcile-1",
        alert_identity="ALERT-R",
        target_type="host",
        target_id="dc-01",
        scope="host-isolation",
    )
    commit_outstanding_directive(store.conn, directive)

    activation = activate_org_config(
        store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
    )
    assert "dir-reconcile-1" in activation.revoked_directive_ids
    assert activation.emitted_alert_ids

    row = store.conn.execute(
        """
        SELECT record_json FROM directive_revocation_records
        WHERE directive_id = ?
        """,
        ("dir-reconcile-1",),
    ).fetchone()
    assert row is not None
    payload = json.loads(str(row["record_json"]))
    assert payload["reason"] == RevocationReason.POST_ACTIVATION_RECONCILIATION.value
    assert payload["idempotency_key_cleared"] is False

    seq_before = read_feed_sequence_next(store.conn)
    feed_row = fetch_feed_outbox_row(store.conn, seq_before - 1)
    assert feed_row is not None
    assert feed_row["directive_id"] == "dir-reconcile-1"

    key_row = store.conn.execute(
        "SELECT cleared_at FROM idempotency_keys WHERE idempotency_key = ?",
        ("idem-reconcile-1",),
    ).fetchone()
    assert key_row is not None
    assert key_row["cleared_at"] is None

    outbox_count = store.conn.execute(
        "SELECT COUNT(*) AS c FROM system_health_alert_outbox"
    ).fetchone()
    assert outbox_count is not None
    assert int(outbox_count["c"]) >= 1

    ledger_rows = fetch_ledger_rows(store.conn)
    assert [row.record_type for row in ledger_rows] == ["directive_revocation"]


def test_reconciliation_skips_expired_and_already_revoked(
    store: StateStore, verifier: PrincipalMapVerifier
) -> None:
    issued = datetime.now(UTC) - timedelta(hours=1)
    expired = ContainmentDirective(
        directive_id="dir-expired",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="dc-01",
        scope="host-isolation",
        evidence_refs=[],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=30),
        idempotency_key="idem-exp",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="x",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )
    commit_outstanding_directive(store.conn, expired)

    activation = activate_org_config(
        store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
    )
    assert "dir-expired" not in activation.revoked_directive_ids


def test_wrong_role_and_missing_token_rejected(store: StateStore) -> None:
    analyst = Principal(identity="analyst-1", role="analyst")
    bad = PrincipalMapVerifier({"t": analyst})
    with pytest.raises(InsufficientRoleError):
        activate_org_config(store, EXAMPLE_CONFIG, token="t", verifier=bad)
    with pytest.raises(MissingTokenError):
        activate_org_config(store, EXAMPLE_CONFIG, token=None, verifier=bad)


def test_revocation_in_transaction_rejected_outside_critical_tx(
    store: StateStore,
) -> None:
    from praetor.contracts.ledger import DirectiveRevocationRecord, RevocationReason

    now = datetime.now(UTC)
    record = DirectiveRevocationRecord(
        revocation_id="rev-outside",
        directive_id="dir-x",
        reason=RevocationReason.NEVER_CONTAIN_CONFLICT,
        reason_code="never_contain_conflict",
        triggered_by="test",
        revoked_at=now,
        ledger_commit_at=now,
        idempotency_key_cleared=False,
    )
    with pytest.raises(StartupGuardError, match="critical_transaction"):
        store.write_automated_revocation_in_transaction(record)


def test_activation_rolls_back_on_injected_revocation_failure(
    store: StateStore, verifier: PrincipalMapVerifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    issued = datetime.now(UTC)
    directive = ContainmentDirective(
        directive_id="dir-rollback",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="dc-01",
        scope="host-isolation",
        evidence_refs=[],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-rb",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="x",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )
    commit_outstanding_directive(store.conn, directive)

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("injected failure")

    monkeypatch.setattr(store, "write_automated_revocation_in_transaction", boom)

    with pytest.raises(RuntimeError, match="injected"):
        activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)

    assert fetch_active_org_config(store.conn) is None
    row = store.conn.execute(
        "SELECT 1 FROM directive_revocation_records WHERE directive_id = ?",
        ("dir-rollback",),
    ).fetchone()
    assert row is None
