"""TASK-018 transactional containment rate limit tests."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

from tests.policy.conftest import (
    NOW,
    auto_contain_judgment,
    host_bundle,
    persist_snapshot_with_overrides,
)

from praetor.contracts.disposition import Disposition
from praetor.contracts.org_config_sections import (
    AssetEntry,
    AssetsAndAssetGroups,
    CircuitBreakerPolicy,
    ContainmentPolicy,
    ContainmentRule,
    RateLimitPolicy,
)
from praetor.policy.containment_policy import resolve_host_target
from praetor.policy.gate import RATE_LIMIT_EXCEEDED, evaluate_policy_gate
from praetor.policy.rate_limit import (
    applicable_rate_limit_scopes,
    rate_limit_scope_key,
    read_scope_event_count,
)
from praetor.state.sqlite_guard import create_guarded_connection


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


def _snapshot_with_registry(store, base, entries: list[AssetEntry]):
    return persist_snapshot_with_overrides(
        store,
        base,
        assets_and_asset_groups=AssetsAndAssetGroups(entries=entries),
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
        rate_limit_policy=RateLimitPolicy(
            scopes=["per_host", "per_subnet", "per_asset_group"]
        ),
        containment_circuit_breaker_policy=CircuitBreakerPolicy(
            window_seconds=300,
            failure_threshold=5,
            success_reset_threshold=3,
        ),
    )


def test_per_host_limit_blocks_second_containment(activated, org_snapshot) -> None:
    snapshot = _snapshot_with_registry(
        activated,
        org_snapshot,
        [
            AssetEntry(asset_id="ws-a", subnet_membership="10.0.1.0/24"),
        ],
    )
    first = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-a"),
        alert_identity="ALERT-HOST-1",
    )
    assert first.final_disposition == Disposition.AUTO_CONTAIN

    second = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-a"),
        alert_identity="ALERT-HOST-2",
    )
    assert second.final_disposition == Disposition.ESCALATE
    assert second.fault_flags == [RATE_LIMIT_EXCEEDED]


def test_per_subnet_limit_blocks_second_host_in_same_subnet(
    activated, org_snapshot
) -> None:
    snapshot = _snapshot_with_registry(
        activated,
        org_snapshot,
        [
            AssetEntry(asset_id="ws-sub-1", subnet_membership="10.20.0.0/24"),
            AssetEntry(asset_id="ws-sub-2", subnet_membership="10.20.0.0/24"),
        ],
    )
    first = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-sub-1"),
        alert_identity="ALERT-SUB-1",
    )
    assert first.final_disposition == Disposition.AUTO_CONTAIN

    second = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-sub-2"),
        alert_identity="ALERT-SUB-2",
    )
    assert second.final_disposition == Disposition.ESCALATE
    assert second.fault_flags == [RATE_LIMIT_EXCEEDED]


def test_per_asset_group_scope_collapses_to_per_host_for_v1(
    activated, org_snapshot
) -> None:
    """v1 per_asset_group uses host asset_id only (DEC-030); not cross-host groups."""
    snapshot = persist_snapshot_with_overrides(
        activated,
        org_snapshot,
        assets_and_asset_groups=AssetsAndAssetGroups(
            entries=[
                AssetEntry(asset_id="pool-a", subnet_membership="10.30.0.0/24"),
            ]
        ),
        containment_policy=ContainmentPolicy(
            precedence=["deny_over_allow"],
            rules=[
                ContainmentRule(
                    name="pool_rule",
                    action="auto_contain",
                    scope={"asset_id": "pool-a"},
                )
            ],
        ),
        rate_limit_policy=RateLimitPolicy(scopes=["per_host", "per_asset_group"]),
        containment_circuit_breaker_policy=CircuitBreakerPolicy(
            window_seconds=300,
            failure_threshold=5,
            success_reset_threshold=3,
        ),
    )
    target = resolve_host_target(host_bundle(host_id="pool-a"))
    assert target is not None
    scopes = applicable_rate_limit_scopes(snapshot, target)
    scope_names = [s.scope_name for s in scopes]
    assert scope_names == ["per_host", "per_asset_group"]
    group_key = rate_limit_scope_key(
        "per_asset_group", target_type="asset_group", target_id="pool-a"
    )
    host_key = rate_limit_scope_key("per_host", target_type="host", target_id="pool-a")
    assert group_key != host_key
    assert group_key.endswith(":pool-a")
    assert host_key.endswith(":pool-a")

    first = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="pool-a"),
        alert_identity="ALERT-POOL-1",
    )
    assert first.final_disposition == Disposition.AUTO_CONTAIN
    assert (
        read_scope_event_count(
            activated.conn, scope_key=host_key, snapshot=snapshot, now=NOW
        )
        == 1
    )
    assert (
        read_scope_event_count(
            activated.conn, scope_key=group_key, snapshot=snapshot, now=NOW
        )
        == 1
    )

    second = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="pool-a"),
        alert_identity="ALERT-POOL-2",
    )
    assert second.final_disposition == Disposition.ESCALATE
    assert second.fault_flags == [RATE_LIMIT_EXCEEDED]


def test_unregistered_host_only_checks_per_host_scope(
    activated, org_snapshot
) -> None:
    snapshot = _snapshot_with_registry(
        activated,
        org_snapshot,
        [AssetEntry(asset_id="dc-01", subnet_membership="10.0.0.0/24")],
    )
    bundle = host_bundle(host_id="ws-unregistered")
    target = resolve_host_target(bundle)
    assert target is not None
    scopes = applicable_rate_limit_scopes(snapshot, target)
    assert [s.scope_name for s in scopes] == ["per_host"]

    first = _gate(
        activated,
        snapshot,
        bundle=bundle,
        alert_identity="ALERT-UNREG-1",
    )
    assert first.final_disposition == Disposition.AUTO_CONTAIN

    subnet_key = rate_limit_scope_key(
        "per_subnet", target_type="subnet", target_id="10.0.0.0/24"
    )
    assert read_scope_event_count(
        activated.conn, scope_key=subnet_key, snapshot=snapshot, now=NOW
    ) == 0


def test_sliding_window_resets_host_limit_after_window(
    activated, org_snapshot
) -> None:
    snapshot = _snapshot_with_registry(
        activated,
        org_snapshot,
        [AssetEntry(asset_id="ws-slide", subnet_membership="10.40.0.0/24")],
    )
    first = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-slide"),
        alert_identity="ALERT-SLIDE-1",
    )
    assert first.final_disposition == Disposition.AUTO_CONTAIN

    blocked = _gate(
        activated,
        snapshot,
        bundle=host_bundle(host_id="ws-slide"),
        alert_identity="ALERT-SLIDE-2",
    )
    assert blocked.final_disposition == Disposition.ESCALATE

    after_window = NOW + timedelta(seconds=301)
    allowed = evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(host_bundle(host_id="ws-slide")),
        evidence_bundle=host_bundle(host_id="ws-slide"),
        org_snapshot=snapshot,
        alert_identity="ALERT-SLIDE-3",
        decision_id="dec-slide-3",
        now=after_window,
    )
    assert allowed.final_disposition == Disposition.AUTO_CONTAIN


def test_in_tx_rate_limit_race_loser_records_single_failure(
    activated, org_snapshot
) -> None:
    """Second connection commits emit between pre-check and in-tx re-check."""
    snapshot = _snapshot_with_registry(
        activated,
        org_snapshot,
        [AssetEntry(asset_id="ws-race", subnet_membership="10.50.0.0/24")],
    )
    bundle = host_bundle(host_id="ws-race")
    conn_a = activated.conn
    conn_b = create_guarded_connection(activated.db_path)
    conn_b.row_factory = sqlite3.Row
    try:

        def winner_commits_before_emit_tx() -> None:
            winner = evaluate_policy_gate(
                conn_b,
                judgment=auto_contain_judgment(bundle),
                evidence_bundle=bundle,
                org_snapshot=snapshot,
                alert_identity="ALERT-RACE-WIN",
                decision_id="dec-race-win",
                now=NOW,
            )
            assert winner.final_disposition == Disposition.AUTO_CONTAIN
            assert winner.containment_directive is not None

        lost = evaluate_policy_gate(
            conn_a,
            judgment=auto_contain_judgment(bundle),
            evidence_bundle=bundle,
            org_snapshot=snapshot,
            alert_identity="ALERT-RACE-LOSE",
            decision_id="dec-race-lose",
            now=NOW,
            _test_before_emit_transaction=winner_commits_before_emit_tx,
        )
        assert lost.final_disposition == Disposition.ESCALATE
        assert lost.fault_flags == [RATE_LIMIT_EXCEEDED]
        assert lost.containment_directive is None

        directive_count = conn_a.execute(
            "SELECT COUNT(*) FROM outstanding_containment_directives"
        ).fetchone()
        assert int(directive_count[0]) == 1

        failure_row = conn_a.execute(
            """
            SELECT failure_count FROM circuit_breaker_state
            WHERE domain = 'containment'
            """
        ).fetchone()
        assert int(failure_row[0]) == 1
    finally:
        conn_b.close()


def test_pre_check_rate_limit_failure_not_double_counted(
    activated, org_snapshot
) -> None:
    snapshot = _snapshot_with_registry(
        activated,
        org_snapshot,
        [AssetEntry(asset_id="ws-dup", subnet_membership="10.55.0.0/24")],
    )
    bundle = host_bundle(host_id="ws-dup")
    _gate(activated, snapshot, bundle=bundle, alert_identity="ALERT-DUP-1")
    blocked = _gate(activated, snapshot, bundle=bundle, alert_identity="ALERT-DUP-2")
    assert blocked.fault_flags == [RATE_LIMIT_EXCEEDED]
    failure_row = activated.conn.execute(
        """
        SELECT failure_count FROM circuit_breaker_state
        WHERE domain = 'containment'
        """
    ).fetchone()
    assert int(failure_row[0]) == 1
