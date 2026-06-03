"""Task 9 — emergency never-contain entries."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from tests.config.helpers import preflight_path
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN

from praetor.auth import InsufficientRoleError
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.directives import commit_outstanding_directive
from praetor.config.emergency import (
    EmergencyNeverContainError,
    add_emergency_never_contain,
    emergency_cannot_authorize_containment,
    evaluate_live_never_contain_for_target,
)
from praetor.config.loader import load_org_config_document
from praetor.config.state import fetch_active_emergency_records
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.ledger import EmergencyNeverContainRecord, RevocationReason
from praetor.state.store import StateStore


def test_emergency_requires_active_org_config(store: StateStore, verifier) -> None:
    with pytest.raises(EmergencyNeverContainError) as exc:
        add_emergency_never_contain(
            store,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={"target_type": "host", "target_id": "eng-99"},
            lifetime_seconds=60,
            audit_reason="test",
        )
    assert exc.value.code == "no_active_org_config"


def test_emergency_persists_outbox_and_revokes_conflict(
    activated: StateStore, verifier
) -> None:
    issued = datetime.now(UTC)
    directive = ContainmentDirective(
        directive_id="dir-emerg-1",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="eng-99",
        scope="host-isolation",
        evidence_refs=["ev-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-emerg",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="sha256:nc:abc",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )
    commit_outstanding_directive(activated.conn, directive)

    result = add_emergency_never_contain(
        activated,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "eng-99"},
        lifetime_seconds=60,
        audit_reason="maintenance",
        entry_id="enc-test-1",
    )
    assert result.emitted_alert_ids
    stored = json.loads(result.record.model_dump_json())
    assert stored["target_specification"] == {
        "target_type": "host",
        "target_id": "eng-99",
    }
    outbox = activated.conn.execute(
        "SELECT COUNT(*) AS c FROM system_health_alert_outbox"
    ).fetchone()
    assert outbox is not None
    assert int(outbox["c"]) >= 2

    row = activated.conn.execute(
        """
        SELECT record_json FROM directive_revocation_records
        WHERE directive_id = ?
        """,
        ("dir-emerg-1",),
    ).fetchone()
    assert row is not None
    assert json.loads(str(row["record_json"]))["reason"] == (
        RevocationReason.NEVER_CONTAIN_CONFLICT.value
    )


def test_emergency_lifetime_bounded_by_org_policy(activated: StateStore, verifier) -> None:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    policy_max = snapshot.emergency_never_contain_policy.max_lifetime_seconds
    with pytest.raises(EmergencyNeverContainError) as exc:
        add_emergency_never_contain(
            activated,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={"target_type": "host", "target_id": "eng-99"},
            lifetime_seconds=policy_max + 1,
            audit_reason="too long",
        )
    assert exc.value.code == "invalid_emergency_lifetime"


def test_legacy_host_shorthand_target_specification_rejected(
    activated: StateStore, verifier
) -> None:
    with pytest.raises(EmergencyNeverContainError) as exc:
        add_emergency_never_contain(
            activated,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={"host": "eng-99"},
            lifetime_seconds=60,
            audit_reason="legacy",
        )
    assert exc.value.code == "invalid_target_specification"


def test_empty_target_specification_rejected(activated: StateStore, verifier) -> None:
    with pytest.raises(EmergencyNeverContainError) as exc:
        add_emergency_never_contain(
            activated,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={},
            lifetime_seconds=60,
            audit_reason="empty",
        )
    assert exc.value.code == "invalid_target_specification"


def test_live_check_includes_emergency_without_purge(
    activated: StateStore, verifier
) -> None:
    add_emergency_never_contain(
        activated,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "eng-99"},
        lifetime_seconds=3600,
        audit_reason="test",
        entry_id="enc-live",
    )
    assert evaluate_live_never_contain_for_target(
        activated, target_type="host", target_id="eng-99"
    )


def test_expired_emergency_excluded_from_live_check(
    activated: StateStore, verifier
) -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    record = EmergencyNeverContainRecord(
        entry_id="enc-expired",
        target_specification={"target_type": "host", "target_id": "stale-host"},
        added_by="soc-lead-1",
        added_at=past,
        expires_at=past + timedelta(hours=1),
        audit_reason="old",
    )
    activated.conn.execute(
        """
        INSERT INTO emergency_never_contain_records (
            entry_id, record_json, added_at, expires_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            record.entry_id,
            record.model_dump_json(),
            record.added_at.isoformat(),
            record.expires_at.isoformat(),
        ),
    )
    assert not evaluate_live_never_contain_for_target(
        activated, target_type="host", target_id="stale-host"
    )
    assert len(fetch_active_emergency_records(activated.conn)) == 0


def test_emergency_auth_rejects_analyst(activated: StateStore) -> None:
    bad = PrincipalMapVerifier(
        {"t": Principal(identity="a", role="analyst")}
    )
    with pytest.raises(InsufficientRoleError):
        add_emergency_never_contain(
            activated,
            token="t",
            verifier=bad,
            target_specification={"target_type": "host", "target_id": "x"},
            lifetime_seconds=60,
            audit_reason="nope",
        )


def test_emergency_cannot_authorize_containment() -> None:
    entries = [{"target_type": "host", "target_id": "eng-99"}]
    assert emergency_cannot_authorize_containment(
        proposed_disposition="auto_contain",
        target_type="host",
        target_id="eng-99",
        live_entries=entries,
    )


def test_activation_reconciles_active_emergency_entries(
    store: StateStore, verifier: PrincipalMapVerifier
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    add_emergency_never_contain(
        store,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "backup-gateway"},
        lifetime_seconds=120,
        audit_reason="bridge",
        entry_id="enc-reconcile",
    )
    issued = datetime.now(UTC)
    directive = ContainmentDirective(
        directive_id="dir-emerg-reconcile",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="backup-gateway",
        scope="host-isolation",
        evidence_refs=[],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=90),
        idempotency_key="idem-bg",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="x",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )
    commit_outstanding_directive(store.conn, directive)

    import yaml

    updated = load_org_config_document(EXAMPLE_CONFIG)
    updated["business_context"]["notes"] = "reconcile with emergency"
    path = store.db_path.parent / "reactivate.yaml"
    path.write_text(yaml.dump(updated), encoding="utf-8")
    result = activate_org_config(store, path, token=SOC_LEAD_TOKEN, verifier=verifier)
    assert "dir-emerg-reconcile" in result.revoked_directive_ids
    assert "enc-reconcile" in result.retired_emergency_entry_ids
    assert len(fetch_active_emergency_records(store.conn)) == 0
