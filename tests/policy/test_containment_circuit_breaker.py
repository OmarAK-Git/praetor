"""TASK-018 containment circuit breaker tests."""

from __future__ import annotations

from datetime import timedelta

from tests.policy.conftest import (
    NOW,
    auto_contain_judgment,
    host_bundle,
    persist_snapshot_with_overrides,
)

from praetor.alerts.outbox import init_health_alert_outbox_schema
from praetor.contracts.disposition import Disposition
from praetor.contracts.org_config_sections import (
    AssetEntry,
    AssetsAndAssetGroups,
    CircuitBreakerPolicy,
    ContainmentPolicy,
    ContainmentRule,
    RateLimitPolicy,
)
from praetor.policy.circuit_breaker import (
    CONTAINMENT_BREAKER_ALERT_CODE,
    is_containment_breaker_open,
    record_containment_success_in_transaction,
    record_rate_limit_failure_in_transaction,
)
from praetor.policy.gate import (
    CONTAINMENT_BREAKER_OPEN,
    RATE_LIMIT_EXCEEDED,
    evaluate_policy_gate,
)
from praetor.policy.rate_limit import rate_limit_scope_key, read_scope_event_count
from praetor.policy.state import init_policy_state_schema
from praetor.state.sqlite_guard import critical_transaction


def _gate(activated, org_snapshot, *, bundle=None, alert_identity: str, **kwargs):
    bundle = bundle or host_bundle()
    judgment = auto_contain_judgment(bundle)
    return evaluate_policy_gate(
        activated.conn,
        judgment=judgment,
        evidence_bundle=bundle,
        org_snapshot=org_snapshot,
        alert_identity=alert_identity,
        decision_id=f"dec-{alert_identity}",
        now=NOW,
        **kwargs,
    )


def _permissive_snapshot(store, base, *, failure_threshold: int = 2):
    return persist_snapshot_with_overrides(
        store,
        base,
        assets_and_asset_groups=AssetsAndAssetGroups(
            entries=[
                AssetEntry(asset_id="ws-br-1", subnet_membership="10.60.0.0/24"),
                AssetEntry(asset_id="ws-br-2", subnet_membership="10.61.0.0/24"),
                AssetEntry(asset_id="ws-br-3", subnet_membership="10.62.0.0/24"),
            ]
        ),
        containment_policy=ContainmentPolicy(
            precedence=["deny_over_allow"],
            rules=[
                ContainmentRule(
                    name="allow_hosts",
                    action="auto_contain",
                    scope={"target_type": "host"},
                )
            ],
        ),
        rate_limit_policy=RateLimitPolicy(scopes=["per_host"]),
        containment_circuit_breaker_policy=CircuitBreakerPolicy(
            window_seconds=300,
            failure_threshold=failure_threshold,
            success_reset_threshold=2,
        ),
    )


def test_sliding_window_failures_trip_containment_breaker(
    activated, org_snapshot
) -> None:
    snapshot = _permissive_snapshot(activated, org_snapshot, failure_threshold=2)
    init_policy_state_schema(activated.conn)
    init_health_alert_outbox_schema(activated.conn)

    first_emit = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-EMIT",
    )
    assert first_emit.final_disposition == Disposition.AUTO_CONTAIN

    fail_one = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-FAIL-1",
    )
    assert fail_one.fault_flags == [RATE_LIMIT_EXCEEDED]
    assert not is_containment_breaker_open(activated.conn)

    fail_two = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-FAIL-2",
    )
    assert fail_two.fault_flags == [RATE_LIMIT_EXCEEDED]
    assert is_containment_breaker_open(activated.conn)


def test_breaker_trip_emits_health_alert(activated, org_snapshot) -> None:
    snapshot = _permissive_snapshot(activated, org_snapshot, failure_threshold=1)
    init_health_alert_outbox_schema(activated.conn)

    _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-EMIT-2",
    )
    trip = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-TRIP",
    )
    assert trip.fault_flags == [RATE_LIMIT_EXCEEDED]
    rows = activated.conn.execute(
        """
        SELECT alert_code FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (CONTAINMENT_BREAKER_ALERT_CODE,),
    ).fetchall()
    assert len(rows) == 1


def test_rate_counters_unchanged_while_breaker_open(
    activated, org_snapshot
) -> None:
    snapshot = _permissive_snapshot(activated, org_snapshot, failure_threshold=1)
    init_policy_state_schema(activated.conn)

    _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-COUNT-EMIT",
    )
    _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-BR-COUNT-TRIP",
    )
    host_key = rate_limit_scope_key(
        "per_host", target_type="host", target_id="ws-br-1"
    )
    count_before = read_scope_event_count(
        activated.conn, scope_key=host_key, snapshot=snapshot, now=NOW
    )

    blocked = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-3"),
        alert_identity="ALERT-BR-COUNT-BLOCKED",
    )
    assert blocked.fault_flags == [CONTAINMENT_BREAKER_OPEN]
    count_after = read_scope_event_count(
        activated.conn, scope_key=host_key, snapshot=snapshot, now=NOW
    )
    assert count_after == count_before


def test_breaker_recovers_after_window_elapses(activated, org_snapshot) -> None:
    snapshot = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        assets_and_asset_groups=AssetsAndAssetGroups(
            entries=[
                AssetEntry(asset_id="ws-rec-1", subnet_membership="10.70.0.0/24"),
                AssetEntry(asset_id="ws-rec-2", subnet_membership="10.71.0.0/24"),
            ]
        ),
        containment_policy=ContainmentPolicy(
            precedence=["deny_over_allow"],
            rules=[
                ContainmentRule(
                    name="allow_hosts",
                    action="auto_contain",
                    scope={"target_type": "host"},
                )
            ],
        ),
        rate_limit_policy=RateLimitPolicy(scopes=["per_host"]),
        containment_circuit_breaker_policy=CircuitBreakerPolicy(
            window_seconds=60,
            failure_threshold=1,
            success_reset_threshold=3,
        ),
    )
    policy = snapshot.containment_circuit_breaker_policy

    _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-rec-1"),
        alert_identity="ALERT-REC-EMIT",
    )
    _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-rec-1"),
        alert_identity="ALERT-REC-TRIP",
    )
    assert is_containment_breaker_open(
        activated.conn, policy=policy, now=NOW
    )

    almost_elapsed = NOW + timedelta(seconds=59)
    still_blocked = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(host_bundle(host_id="ws-rec-2")),
        evidence_bundle=host_bundle(host_id="ws-rec-2"),
        org_snapshot=snapshot,
        alert_identity="ALERT-REC-BLOCKED",
        decision_id="dec-rec-blocked",
        now=almost_elapsed,
    )
    assert still_blocked.fault_flags == [CONTAINMENT_BREAKER_OPEN]

    elapsed = NOW + timedelta(seconds=60)
    recovered = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(host_bundle(host_id="ws-rec-2")),
        evidence_bundle=host_bundle(host_id="ws-rec-2"),
        org_snapshot=snapshot,
        alert_identity="ALERT-REC-OPEN",
        decision_id="dec-rec-open",
        now=elapsed,
    )
    assert recovered.final_disposition == Disposition.AUTO_CONTAIN
    assert not is_containment_breaker_open(
        activated.conn, policy=policy, now=elapsed
    )


def test_gate_breaker_trip_without_preinitialized_outbox(
    activated, org_snapshot
) -> None:
    activated.conn.executescript(
        """
        DROP TABLE IF EXISTS system_health_delivery_attempts;
        DROP INDEX IF EXISTS idx_health_alert_pending_unflushed;
        DROP TABLE IF EXISTS health_alert_pending_flush;
        DROP TABLE IF EXISTS system_health_alert_outbox;
        """
    )
    snapshot = _permissive_snapshot(activated, org_snapshot, failure_threshold=1)

    _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-OUTBOX-EMIT",
    )
    trip = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-br-1"),
        alert_identity="ALERT-OUTBOX-TRIP",
    )
    assert trip.fault_flags == [RATE_LIMIT_EXCEEDED]
    rows = activated.conn.execute(
        """
        SELECT alert_code FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (CONTAINMENT_BREAKER_ALERT_CODE,),
    ).fetchall()
    assert len(rows) == 1


def test_success_reset_threshold_clears_failure_state(
    activated, org_snapshot
) -> None:
    policy = CircuitBreakerPolicy(
        window_seconds=300,
        failure_threshold=5,
        success_reset_threshold=2,
    )
    init_policy_state_schema(activated.conn)

    with critical_transaction(activated.conn):
        record_rate_limit_failure_in_transaction(
            activated.conn, policy=policy, now=NOW
        )

    with critical_transaction(activated.conn):
        first_reset = record_containment_success_in_transaction(
            activated.conn, policy=policy, now=NOW
        )
        assert not first_reset

    with critical_transaction(activated.conn):
        second_reset = record_containment_success_in_transaction(
            activated.conn, policy=policy, now=NOW
        )
        assert second_reset

    row = activated.conn.execute(
        """
        SELECT failure_count, success_count
        FROM circuit_breaker_state
        WHERE domain = 'containment'
        """
    ).fetchone()
    assert int(row[0]) == 0
    assert int(row[1]) == 0
