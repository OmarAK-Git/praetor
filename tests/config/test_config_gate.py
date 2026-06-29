"""TASK-009 gate tests: integrity, locks, health durability, contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from tests.config.helpers import preflight_document, preflight_loaded, preflight_path
from tests.config.shared import EXAMPLE_CONFIG, EXAMPLE_SNAPSHOT_HASH, SOC_LEAD_TOKEN

import praetor.config as config_pkg
from praetor.config import activation as activation_mod
from praetor.config import emergency as emergency_mod
from praetor.config.activation import activate_org_config
from praetor.config.emergency import (
    EmergencyNeverContainError,
    add_emergency_never_contain,
)
from praetor.config.errors import (
    PreflightError,
    SnapshotHashConflictError,
    SnapshotTamperError,
)
from praetor.config.health_emit import flush_health_alert_batch
from praetor.config.loader import load_org_config_source
from praetor.config.snapshot import compute_snapshot_hash, verbatim_character_count
from praetor.config.state import (
    fetch_snapshot_by_hash,
    fetch_verbatim_render_text,
    init_config_schema,
    persist_org_config_snapshot,
)
from praetor.hashing import ORG_CONFIG_SNAPSHOT_HASH_KEYS
from praetor.state import sqlite_guard
from praetor.state.store import open_state_store


def test_hash_keys_match_generated_schema_properties() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "org_config_snapshot.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props = set(schema["properties"].keys()) - {"snapshot_hash"}
    assert set(ORG_CONFIG_SNAPSHOT_HASH_KEYS) == props


def test_same_hash_conflicting_body_rejected(store) -> None:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    persist_org_config_snapshot(
        store.conn, snapshot, verbatim_render_text="first"
    )
    corrupt = snapshot.model_dump_json()
    corrupt = corrupt.replace("Example org", "Conflicting binding body")
    store.conn.execute(
        "UPDATE org_config_snapshots SET snapshot_json = ? WHERE snapshot_hash = ?",
        (corrupt, snapshot.snapshot_hash),
    )
    with pytest.raises(SnapshotHashConflictError):
        persist_org_config_snapshot(
            store.conn, snapshot, verbatim_render_text="second"
        )


def test_stored_snapshot_hash_field_mismatch_rejected_on_fetch(store) -> None:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    persist_org_config_snapshot(
        store.conn, snapshot, verbatim_render_text="ok"
    )
    payload = snapshot.model_dump(mode="json")
    payload["snapshot_hash"] = "evil"
    store.conn.execute(
        "UPDATE org_config_snapshots SET snapshot_json = ? WHERE snapshot_hash = ?",
        (json.dumps(payload), snapshot.snapshot_hash),
    )
    with pytest.raises(SnapshotTamperError, match="snapshot_hash field mismatch"):
        fetch_snapshot_by_hash(store.conn, snapshot.snapshot_hash)


def test_tampered_snapshot_row_rejected_on_fetch(store) -> None:
    snapshot = preflight_path(EXAMPLE_CONFIG)
    persist_org_config_snapshot(
        store.conn, snapshot, verbatim_render_text="ok"
    )
    corrupt = snapshot.model_dump_json()
    corrupt = corrupt.replace("Example org", "Tampered org")
    store.conn.execute(
        "UPDATE org_config_snapshots SET snapshot_json = ? WHERE snapshot_hash = ?",
        (corrupt, snapshot.snapshot_hash),
    )
    with pytest.raises(SnapshotTamperError):
        fetch_snapshot_by_hash(store.conn, snapshot.snapshot_hash)


def test_snapshot_survives_close_and_reopen(tmp_path: Path) -> None:
    db = tmp_path / "persist.db"
    snapshot = preflight_path(EXAMPLE_CONFIG)
    s1 = open_state_store(db)
    init_config_schema(s1.conn)
    persist_org_config_snapshot(
        s1.conn, snapshot, verbatim_render_text="verbatim-bytes"
    )
    s1.close()
    s2 = open_state_store(db)
    init_config_schema(s2.conn)
    loaded = fetch_snapshot_by_hash(s2.conn, snapshot.snapshot_hash)
    assert loaded is not None
    assert compute_snapshot_hash(loaded) == snapshot.snapshot_hash
    assert (
        fetch_verbatim_render_text(s2.conn, snapshot.snapshot_hash)
        == "verbatim-bytes"
    )
    s2.close()


def test_same_binding_hash_stores_multiple_verbatim_renders(
    store, verifier, tmp_path: Path
) -> None:
    loaded_a = load_org_config_source(EXAMPLE_CONFIG)
    snap = preflight_loaded(loaded_a)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    text_b = loaded_a.verbatim_text + "\n# activation comment\n"
    path_b = tmp_path / "commented.yaml"
    path_b.write_text(text_b, encoding="utf-8")
    activate_org_config(store, path_b, token=SOC_LEAD_TOKEN, verifier=verifier)
    active = store.conn.execute(
        "SELECT verbatim_render_id FROM active_org_config WHERE id = 1"
    ).fetchone()
    assert active is not None
    active_id = str(active["verbatim_render_id"])
    assert (
        fetch_verbatim_render_text(
            store.conn, snap.snapshot_hash, verbatim_render_id=active_id
        )
        == text_b
    )
    count = store.conn.execute(
        "SELECT COUNT(*) AS c FROM org_config_verbatim_renders WHERE snapshot_hash = ?",
        (snap.snapshot_hash,),
    ).fetchone()
    assert count is not None
    assert int(count["c"]) >= 2


def test_verbatim_budget_differs_for_comment_whitespace_same_hash(tmp_path: Path) -> None:
    loaded_a = load_org_config_source(EXAMPLE_CONFIG)
    snap_a = preflight_loaded(loaded_a)
    text_b = loaded_a.verbatim_text + "\n# trailing comment preserved\n"
    path_b = tmp_path / "commented.yaml"
    path_b.write_text(text_b, encoding="utf-8")
    loaded_b = load_org_config_source(path_b)
    snap_b = preflight_loaded(loaded_b)
    assert snap_a.snapshot_hash == snap_b.snapshot_hash
    assert verbatim_character_count(text_b) > verbatim_character_count(
        loaded_a.verbatim_text
    )


def test_health_flush_retries_after_injected_failure(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:

    from praetor.config.health_emit import (
        enqueue_health_alerts_in_transaction,
        new_health_alert_batch_id,
    )
    from praetor.contracts.health import SystemHealthAlert
    from praetor.state.sqlite_guard import critical_transaction

    batch_id = new_health_alert_batch_id()
    alert = SystemHealthAlert(
        alert_code="never_contain_post_activation_conflict",
        emitted_at=datetime.now(UTC),
    )
    with critical_transaction(store.conn):
        enqueue_health_alerts_in_transaction(store.conn, [alert], batch_id=batch_id)

    calls: list[int] = []

    def flaky(conn, alert, *, alert_id=None):  # type: ignore[no-untyped-def]
        calls.append(1)
        if len(calls) == 1:
            raise OSError("injected outbox failure")
        from praetor.alerts.outbox import write_pending_health_alert

        return write_pending_health_alert(conn, alert, alert_id=alert_id)

    monkeypatch.setattr(
        "praetor.config.health_emit.write_pending_health_alert",
        flaky,
    )
    with pytest.raises(OSError, match="injected"):
        flush_health_alert_batch(store.conn, batch_id=batch_id)

    pending = store.conn.execute(
        "SELECT COUNT(*) AS c FROM health_alert_pending_flush WHERE flushed = 0"
    ).fetchone()
    assert pending is not None
    assert int(pending["c"]) == 1

    recovered = flush_health_alert_batch(store.conn, batch_id=batch_id)
    assert len(recovered) == 1
    again = flush_health_alert_batch(store.conn, batch_id=batch_id)
    assert again == []


def test_activation_fetches_emergencies_inside_critical_transaction(
    store, verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    from praetor.config import state as state_mod

    seen: list[bool] = []
    original = state_mod.fetch_active_emergency_records

    def wrapped(conn, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(sqlite_guard._in_critical.get(id(conn), False))
        return original(conn, **kwargs)

    monkeypatch.setattr(
        activation_mod,
        "fetch_active_emergency_records",
        wrapped,
    )
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    assert seen == [True]


def test_emergency_policy_read_inside_critical_transaction(
    store, verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    seen: list[bool] = []
    original = emergency_mod.fetch_active_snapshot

    def wrapped(conn):  # type: ignore[no-untyped-def]
        seen.append(sqlite_guard._in_critical.get(id(conn), False))
        return original(conn)

    monkeypatch.setattr(emergency_mod, "fetch_active_snapshot", wrapped)
    add_emergency_never_contain(
        store,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "eng-99"},
        lifetime_seconds=60,
        audit_reason="lock check",
    )
    assert seen == [True]


def test_emergency_lifetime_bounded_by_snapshot_read_in_transaction(
    store, verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    strict = preflight_path(EXAMPLE_CONFIG)
    strict = strict.model_copy(
        update={
            "emergency_never_contain_policy": strict.emergency_never_contain_policy.model_copy(
                update={"max_lifetime_seconds": 60}
            )
        }
    )
    monkeypatch.setattr(emergency_mod, "fetch_active_snapshot", lambda conn: strict)
    with pytest.raises(EmergencyNeverContainError) as exc:
        add_emergency_never_contain(
            store,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={"target_type": "host", "target_id": "race-host"},
            lifetime_seconds=120,
            audit_reason="policy bound in transaction",
        )
    assert exc.value.code == "invalid_emergency_lifetime"


def test_public_config_surface_excludes_unauthenticated_persist() -> None:
    assert "persist_org_config_snapshot" not in config_pkg.__all__
    assert "purge_expired_emergency_records" not in dir(config_pkg)


def test_phase3_self_attest_does_not_bypass_account_gate() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["version_metadata"]["phase_3_identity_gates_passed"] = True
    doc["account_auto_contain_enabled"] = True
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "account_containment_prerequisite"


def test_emergency_lifetime_rejects_bool_and_float(activated, verifier) -> None:
    for bad in (True, 1.5):
        with pytest.raises(EmergencyNeverContainError) as exc:
            add_emergency_never_contain(
                activated,
                token=SOC_LEAD_TOKEN,
                verifier=verifier,
                target_specification={"target_type": "host", "target_id": "eng-99"},
                lifetime_seconds=bad,  # type: ignore[arg-type]
                audit_reason="bad type",
            )
        assert exc.value.code == "invalid_emergency_lifetime"


def test_directive_lifetime_string_coercion_rejected() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["directive_lifetime_policy"]["max_lifetime_seconds"] = "300"
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_directive_lifetime"


def test_probe_rate_string_coercion_rejected() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["provider_health_circuit_breaker_policy"]["probe_rate_limit_per_minute"] = "10"
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_section"


def test_business_context_float_invalid_binding_value() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["business_context"]["risk_score"] = 1.5
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_binding_value"


def test_activation_drains_unflushed_health_after_prior_flush_failure(
    store, verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    from praetor.config.directives import commit_outstanding_directive
    from praetor.contracts.containment import (
        ContainmentDirective,
        DirectiveStatus,
        TargetType,
    )

    issued = datetime.now(UTC)
    directive = ContainmentDirective(
        directive_id="dir-drain-activation",
        decision_id="dec-1",
        target_type=TargetType.HOST,
        target_id="dc-01",
        scope="host-isolation",
        evidence_refs=[],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-drain",
        actuator_constraints={},
        revocation_policy={},
        status=DirectiveStatus.EMITTED,
        live_never_contain_hash="x",
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=1,
    )
    commit_outstanding_directive(store.conn, directive)
    calls: list[int] = []

    def flaky(conn, alert, *, alert_id=None):  # type: ignore[no-untyped-def]
        calls.append(1)
        if len(calls) == 1:
            raise OSError("injected outbox failure")
        from praetor.alerts.outbox import write_pending_health_alert

        return write_pending_health_alert(conn, alert, alert_id=alert_id)

    monkeypatch.setattr(
        "praetor.config.health_emit.write_pending_health_alert",
        flaky,
    )
    with pytest.raises(OSError, match="injected"):
        activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)

    pending = store.conn.execute(
        "SELECT COUNT(*) AS c FROM health_alert_pending_flush WHERE flushed = 0"
    ).fetchone()
    assert pending is not None
    assert int(pending["c"]) >= 1
    outbox_before = store.conn.execute(
        "SELECT COUNT(*) AS c FROM system_health_alert_outbox"
    ).fetchone()
    assert outbox_before is not None
    assert int(outbox_before["c"]) == 0

    result = activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    assert result.emitted_alert_ids
    outbox_after = store.conn.execute(
        "SELECT COUNT(*) AS c FROM system_health_alert_outbox"
    ).fetchone()
    assert outbox_after is not None
    assert int(outbox_after["c"]) >= 1
    unflushed = store.conn.execute(
        "SELECT COUNT(*) AS c FROM health_alert_pending_flush WHERE flushed = 0"
    ).fetchone()
    assert unflushed is not None
    assert int(unflushed["c"]) == 0


def test_provisional_throughput_coercion_rejected() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["provisional_alert_rate_targets"]["sustained_alerts_per_minute"] = "30"
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "missing_provisional_targets"


def test_provider_breaker_missing_probe_rate_rejected() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    del doc["provider_health_circuit_breaker_policy"]["probe_rate_limit_per_minute"]
    with pytest.raises(PreflightError):
        preflight_document(doc)


def test_activation_rejects_string_containment_rule_scope() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["containment_policy"]["rules"] = [
        {"name": "broken", "action": "escalate", "scope": "global"},
    ]
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_containment_rule_scope"


def test_asset_groups_extra_field_allowed() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["assets_and_asset_groups"]["asset_groups"] = [{"group_id": "eng-pool"}]
    snapshot = preflight_document(doc)
    assert snapshot.assets_and_asset_groups.model_dump(mode="json").get(
        "asset_groups"
    )


def test_account_target_requires_sid() -> None:
    doc = load_org_config_source(EXAMPLE_CONFIG).document
    doc["containment_exclusions"]["never_contain"].append(
        {"target_type": "account", "target_id": "DOMAIN\\user"}
    )
    with pytest.raises(PreflightError) as exc:
        preflight_document(doc)
    assert exc.value.code == "invalid_target_specification"


def test_emergency_survives_activation_when_not_in_permanent(
    store, verifier, tmp_path: Path
) -> None:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    add_emergency_never_contain(
        store,
        token=SOC_LEAD_TOKEN,
        verifier=verifier,
        target_specification={"target_type": "host", "target_id": "eng-99"},
        lifetime_seconds=120,
        audit_reason="survive",
        entry_id="enc-survive",
    )
    updated = load_org_config_source(EXAMPLE_CONFIG)
    updated.document["business_context"]["notes"] = "bump"
    path = tmp_path / "bump.yaml"
    path.write_text(yaml.dump(updated.document), encoding="utf-8")
    result = activate_org_config(store, path, token=SOC_LEAD_TOKEN, verifier=verifier)
    assert "enc-survive" not in result.retired_emergency_entry_ids
    row = store.conn.execute(
        "SELECT 1 FROM emergency_never_contain_records WHERE entry_id = ?",
        ("enc-survive",),
    ).fetchone()
    assert row is not None


def test_example_hash_matches_contract_vector() -> None:
    assert preflight_path(EXAMPLE_CONFIG).snapshot_hash == EXAMPLE_SNAPSHOT_HASH
