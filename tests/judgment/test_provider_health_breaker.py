"""TASK-019 provider-health breaker with half-open probes."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN
from tests.policy.conftest import NOW, auto_contain_judgment, host_bundle

from praetor.auth.principal import InsufficientRoleError, Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.health_emit import (
    flush_health_alert_batch,
    init_health_alert_emit_schema,
)
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.org_config_sections import ProviderHealthCircuitBreakerPolicy
from praetor.judgment.fake_provider import FakeProvider
from praetor.judgment.provider import (
    PROVIDER_HEALTH_CANARY_PAYLOAD,
    JudgmentProvider,
    JudgmentRequest,
    ProviderOutputTruncatedError,
    ProviderProbeResult,
    ProviderUnavailableError,
)
from praetor.judgment.provider_health_breaker import (
    PROVIDER_HEALTH_BREAKER_ALERT_CODE,
    execute_provider_health_probe,
    init_provider_health_breaker_schema,
    is_provider_health_breaker_blocking,
    is_provider_health_half_open,
    maybe_enter_half_open_from_timer,
    provider_failure_trips_breaker,
    read_provider_health_metrics,
    record_provider_production_failure_in_transaction,
    record_provider_production_success_in_transaction,
    trigger_half_open_probes_by_soc_lead,
)
from praetor.policy.circuit_breaker import (
    CONTAINMENT_BREAKER_ALERT_CODE,
    record_rate_limit_failure_in_transaction,
)
from praetor.policy.gate import PROVIDER_HEALTH_BREAKER_OPEN, evaluate_policy_gate
from praetor.policy.state import BreakerDomain, is_breaker_open
from praetor.runtime.singleton import SingletonLock
from praetor.runtime.startup import open_production_state_store
from praetor.state.sqlite_guard import (
    StartupGuardError,
    critical_transaction,
    init_state_dir,
)
from praetor.state.store import StateStore, open_state_store

SOC_LEAD = Principal(identity="soc-lead-1", role="soc_lead")


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    s = open_state_store(db)
    yield s
    s.close()


@pytest.fixture
def activated(store: StateStore, verifier: PrincipalMapVerifier) -> StateStore:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    return store


@pytest.fixture
def provider_policy(activated: StateStore) -> ProviderHealthCircuitBreakerPolicy:
    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    return snapshot.provider_health_circuit_breaker_policy


def _trip_policy(*, failure_threshold: int = 2) -> ProviderHealthCircuitBreakerPolicy:
    return ProviderHealthCircuitBreakerPolicy(
        window_seconds=60,
        failure_threshold=failure_threshold,
        success_reset_threshold=2,
        probe_rate_limit_per_minute=2,
    )


def _record_failure(
    conn,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime = NOW,
):
    init_health_alert_emit_schema(conn)
    init_provider_health_breaker_schema(conn)
    with critical_transaction(conn):
        trip = record_provider_production_failure_in_transaction(
            conn, policy=policy, now=now
        )
    if trip.health_alert_batch_id is not None:
        flush_health_alert_batch(conn, batch_id=trip.health_alert_batch_id)
    return trip


def _open_breaker(
    activated: StateStore,
    *,
    policy: ProviderHealthCircuitBreakerPolicy | None = None,
) -> ProviderHealthCircuitBreakerPolicy:
    policy = policy or _trip_policy(failure_threshold=1)
    _record_failure(activated.conn, policy=policy)
    assert is_provider_health_breaker_blocking(activated.conn)
    return policy


def _trigger_half_open(conn, *, now: datetime = NOW) -> bool:
    with critical_transaction(conn):
        return trigger_half_open_probes_by_soc_lead(
            conn, principal=SOC_LEAD, now=now
        )


def _maybe_timer_half_open(
    conn,
    *,
    policy: ProviderHealthCircuitBreakerPolicy,
    now: datetime,
) -> bool:
    with critical_transaction(conn):
        return maybe_enter_half_open_from_timer(conn, policy=policy, now=now)


class _ProbeTrackingProvider:
    def __init__(self, *, probe_success: bool = True) -> None:
        self.probe_success = probe_success
        self.probe_calls = 0
        self.generate_calls = 0
        self.last_canary: Mapping[str, Any] | None = None

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.generate_calls += 1
        raise ProviderUnavailableError("production call blocked in probe test")

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        self.probe_calls += 1
        self.last_canary = canary_payload
        return ProviderProbeResult(
            success=self.probe_success,
            provider_name="probe-test",
            model_name="probe-test",
            metadata={"canary_seen": bool(canary_payload)},
        )


@pytest.fixture
def org_snapshot(activated: StateStore):
    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    return snapshot


def _gate(activated: StateStore, snapshot, *, alert_identity: str):
    return evaluate_policy_gate(
        activated.conn,
        judgment=auto_contain_judgment(host_bundle()),
        evidence_bundle=host_bundle(),
        org_snapshot=snapshot,
        alert_identity=alert_identity,
        decision_id=f"dec-{alert_identity}",
        now=NOW,
    )


def test_provider_unavailable_trips_breaker() -> None:
    assert provider_failure_trips_breaker(ProviderUnavailableError("stub"))


def test_provider_output_truncated_trips_breaker() -> None:
    assert provider_failure_trips_breaker(
        ProviderOutputTruncatedError("finishReason=MAX_TOKENS")
    )


def test_provider_failures_trip_breaker(activated: StateStore) -> None:
    policy = _trip_policy(failure_threshold=2)
    _record_failure(activated.conn, policy=policy)
    assert not is_provider_health_breaker_blocking(activated.conn)

    _record_failure(activated.conn, policy=policy)
    assert is_provider_health_breaker_blocking(activated.conn)
    assert not is_provider_health_half_open(activated.conn)


def test_breaker_trip_emits_distinct_health_alert(activated: StateStore) -> None:
    _open_breaker(activated)

    rows = activated.conn.execute(
        """
        SELECT alert_code FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (PROVIDER_HEALTH_BREAKER_ALERT_CODE,),
    ).fetchall()
    assert len(rows) == 1
    assert all(row[0] != CONTAINMENT_BREAKER_ALERT_CODE for row in rows)


def test_production_escalates_while_breaker_open(activated, org_snapshot) -> None:
    _open_breaker(activated)
    result = _gate(
        activated,
        org_snapshot,
        alert_identity="ALERT-PHB-OPEN",
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [PROVIDER_HEALTH_BREAKER_OPEN]
    assert result.system_fault_escalation is True


def test_soc_lead_trigger_enters_half_open(activated: StateStore) -> None:
    _open_breaker(activated)

    entered = _trigger_half_open(activated.conn, now=NOW)
    assert entered is True
    assert is_provider_health_half_open(activated.conn)
    assert is_provider_health_breaker_blocking(activated.conn)


def test_soc_lead_role_required_for_half_open_trigger(activated: StateStore) -> None:
    _open_breaker(activated)
    analyst = Principal(identity="analyst-1", role="analyst")
    with pytest.raises(InsufficientRoleError):
        with critical_transaction(activated.conn):
            trigger_half_open_probes_by_soc_lead(
                activated.conn, principal=analyst, now=NOW
            )


def test_timer_enters_half_open(activated: StateStore) -> None:
    policy = _open_breaker(activated)
    too_soon = NOW + timedelta(seconds=59)
    assert not _maybe_timer_half_open(activated.conn, policy=policy, now=too_soon)
    assert not is_provider_health_half_open(activated.conn)

    elapsed = NOW + timedelta(seconds=60)
    assert _maybe_timer_half_open(activated.conn, policy=policy, now=elapsed)
    assert is_provider_health_half_open(activated.conn)


def test_probe_uses_canary_only(activated: StateStore) -> None:
    policy = _open_breaker(activated)
    _trigger_half_open(activated.conn, now=NOW)
    provider = _ProbeTrackingProvider(probe_success=True)
    with critical_transaction(activated.conn):
        result = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert result.executed is True
    assert provider.probe_calls == 1
    assert provider.generate_calls == 0
    assert provider.last_canary == PROVIDER_HEALTH_CANARY_PAYLOAD


def test_probe_rate_limited(activated: StateStore) -> None:
    policy = ProviderHealthCircuitBreakerPolicy(
        window_seconds=60,
        failure_threshold=1,
        success_reset_threshold=5,
        probe_rate_limit_per_minute=2,
    )
    _open_breaker(activated, policy=policy)
    _trigger_half_open(activated.conn, now=NOW)
    provider = _ProbeTrackingProvider(probe_success=True)
    with critical_transaction(activated.conn):
        first = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
        second = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
        third = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert first.executed and not first.rate_limited
    assert second.executed and not second.rate_limited
    assert third.rate_limited is True
    assert provider.probe_calls == 2


def test_probe_metrics_independent_from_production(activated: StateStore) -> None:
    policy = _trip_policy(failure_threshold=1)
    _record_failure(activated.conn, policy=policy)
    with critical_transaction(activated.conn):
        record_provider_production_failure_in_transaction(
            activated.conn, policy=policy, now=NOW
        )

    metrics = read_provider_health_metrics(activated.conn)
    assert metrics.production_failure_total == 2
    assert metrics.probe_success_total == 0
    assert metrics.probe_failure_total == 0


def test_probe_failure_reopens_breaker(activated: StateStore) -> None:
    policy = _open_breaker(activated)
    _trigger_half_open(activated.conn, now=NOW)
    with critical_transaction(activated.conn):
        execute_provider_health_probe(
            activated.conn,
            _ProbeTrackingProvider(probe_success=True),
            policy=policy,
            now=NOW,
        )
    assert is_provider_health_half_open(activated.conn)

    provider = _ProbeTrackingProvider(probe_success=False)
    with critical_transaction(activated.conn):
        result = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert result.probe_success is False
    assert is_provider_health_breaker_blocking(activated.conn)
    assert not is_provider_health_half_open(activated.conn)
    row = activated.conn.execute(
        """
        SELECT success_count FROM circuit_breaker_state
        WHERE domain = ?
        """,
        (BreakerDomain.PROVIDER_HEALTH.value,),
    ).fetchone()
    assert int(row[0]) == 0
    metrics = read_provider_health_metrics(activated.conn)
    assert metrics.probe_failure_total == 1


def test_consecutive_probe_successes_close_breaker(activated: StateStore) -> None:
    policy = _open_breaker(activated)
    _trigger_half_open(activated.conn, now=NOW)
    provider = _ProbeTrackingProvider(probe_success=True)
    with critical_transaction(activated.conn):
        first = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
        assert first.breaker_closed is False
        second = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert second.breaker_closed is True
    assert not is_provider_health_breaker_blocking(activated.conn)
    metrics = read_provider_health_metrics(activated.conn)
    assert metrics.probe_success_total == 2


def test_breaker_domains_independent(activated: StateStore, provider_policy) -> None:
    init_health_alert_emit_schema(activated.conn)
    init_provider_health_breaker_schema(activated.conn)
    containment_policy = fetch_active_snapshot(activated.conn)
    assert containment_policy is not None

    _open_breaker(activated, policy=_trip_policy(failure_threshold=1))
    assert is_breaker_open(activated.conn, BreakerDomain.PROVIDER_HEALTH)
    assert not is_breaker_open(activated.conn, BreakerDomain.CONTAINMENT)

    with critical_transaction(activated.conn):
        record_rate_limit_failure_in_transaction(
            activated.conn,
            policy=containment_policy.containment_circuit_breaker_policy.model_copy(
                update={"failure_threshold": 1}
            ),
            now=NOW,
        )
    assert is_breaker_open(activated.conn, BreakerDomain.CONTAINMENT)
    assert is_breaker_open(activated.conn, BreakerDomain.PROVIDER_HEALTH)


def test_production_escalates_during_half_open(activated, org_snapshot) -> None:
    _open_breaker(activated)
    _trigger_half_open(activated.conn, now=NOW)
    result = _gate(
        activated,
        org_snapshot,
        alert_identity="ALERT-PHB-HALF-OPEN",
    )
    assert result.final_disposition == Disposition.ESCALATE
    assert result.fault_flags == [PROVIDER_HEALTH_BREAKER_OPEN]


def test_probe_failure_restarts_half_open_timer_cooldown(activated: StateStore) -> None:
    policy = ProviderHealthCircuitBreakerPolicy(
        window_seconds=60,
        failure_threshold=1,
        success_reset_threshold=2,
        probe_rate_limit_per_minute=10,
    )
    _open_breaker(activated, policy=policy)
    half_open_at = NOW + timedelta(seconds=60)
    assert _maybe_timer_half_open(activated.conn, policy=policy, now=half_open_at)

    with critical_transaction(activated.conn):
        execute_provider_health_probe(
            activated.conn,
            _ProbeTrackingProvider(probe_success=False),
            policy=policy,
            now=half_open_at,
        )

    assert not is_provider_health_half_open(activated.conn)
    assert not _maybe_timer_half_open(
        activated.conn,
        policy=policy,
        now=half_open_at + timedelta(seconds=1),
    )
    assert _maybe_timer_half_open(
        activated.conn,
        policy=policy,
        now=half_open_at + timedelta(seconds=60),
    )


def test_production_startup_schema_ready_for_failure_record(tmp_path: Path) -> None:
    db = tmp_path / "prod-phb.db"
    init_state_dir(db)
    policy = _trip_policy(failure_threshold=1)
    with SingletonLock(tmp_path) as lock:
        store = open_production_state_store(db, singleton=lock)
        init_health_alert_emit_schema(store.conn)
        with critical_transaction(store.conn):
            trip = record_provider_production_failure_in_transaction(
                store.conn, policy=policy, now=NOW
            )
        assert trip.newly_opened is True
        assert is_provider_health_breaker_blocking(store.conn)
        store.close()


def test_open_state_store_reconcile_inits_provider_health_schema(
    tmp_path: Path,
) -> None:
    db = tmp_path / "state.db"
    init_state_dir(db)
    store = open_state_store(db)
    row = store.conn.execute(
        "SELECT COUNT(*) FROM provider_health_metrics WHERE id = 1"
    ).fetchone()
    assert row is not None and int(row[0]) == 1
    columns = {
        str(r[1])
        for r in store.conn.execute("PRAGMA table_info(circuit_breaker_state)")
    }
    assert "half_open" in columns
    assert "opened_at" in columns
    store.close()


def test_init_forbidden_inside_critical_transaction(activated: StateStore) -> None:
    init_provider_health_breaker_schema(activated.conn)
    with critical_transaction(activated.conn):
        with pytest.raises(
            StartupGuardError, match="cannot run inside critical_transaction"
        ):
            is_provider_health_breaker_blocking(activated.conn)


def test_full_retrip_cycle_emits_second_health_alert(activated: StateStore) -> None:
    policy = _trip_policy(failure_threshold=1)
    _open_breaker(activated, policy=policy)
    _trigger_half_open(activated.conn)
    provider = _ProbeTrackingProvider(probe_success=True)
    with critical_transaction(activated.conn):
        execute_provider_health_probe(activated.conn, provider, policy=policy, now=NOW)
        execute_provider_health_probe(activated.conn, provider, policy=policy, now=NOW)
    assert not is_provider_health_breaker_blocking(activated.conn)

    _open_breaker(activated, policy=policy)
    rows = activated.conn.execute(
        """
        SELECT alert_code FROM system_health_alert_outbox
        WHERE alert_code = ?
        """,
        (PROVIDER_HEALTH_BREAKER_ALERT_CODE,),
    ).fetchall()
    assert len(rows) == 2


def test_failure_window_expiry_prevents_trip(activated: StateStore) -> None:
    policy = _trip_policy(failure_threshold=2)
    _record_failure(activated.conn, policy=policy, now=NOW)
    _record_failure(
        activated.conn,
        policy=policy,
        now=NOW + timedelta(seconds=61),
    )
    assert not is_provider_health_breaker_blocking(activated.conn)


def test_execute_probe_skipped_when_not_half_open(activated: StateStore) -> None:
    policy = _trip_policy(failure_threshold=1)
    provider = _ProbeTrackingProvider()

    with critical_transaction(activated.conn):
        closed = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert closed.executed is False
    assert provider.probe_calls == 0

    _open_breaker(activated, policy=policy)
    with critical_transaction(activated.conn):
        open_not_half = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert open_not_half.executed is False
    assert provider.probe_calls == 0


def test_soc_lead_trigger_on_closed_breaker_is_noop(activated: StateStore) -> None:
    assert not is_provider_health_breaker_blocking(activated.conn)
    assert not _trigger_half_open(activated.conn, now=NOW)
    assert not is_provider_health_half_open(activated.conn)


def test_probe_rate_limit_rollover_after_minute(activated: StateStore) -> None:
    policy = ProviderHealthCircuitBreakerPolicy(
        window_seconds=60,
        failure_threshold=1,
        success_reset_threshold=5,
        probe_rate_limit_per_minute=1,
    )
    _open_breaker(activated, policy=policy)
    _trigger_half_open(activated.conn, now=NOW)
    provider = _ProbeTrackingProvider(probe_success=True)
    with critical_transaction(activated.conn):
        first = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
        blocked = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=NOW
        )
    assert first.executed is True
    assert blocked.rate_limited is True
    assert provider.probe_calls == 1

    later = NOW + timedelta(seconds=61)
    with critical_transaction(activated.conn):
        after_rollover = execute_provider_health_probe(
            activated.conn, provider, policy=policy, now=later
        )
    assert after_rollover.executed is True
    assert provider.probe_calls == 2


def test_production_success_metrics_while_closed_only(activated: StateStore) -> None:
    policy = _trip_policy(failure_threshold=1)
    init_provider_health_breaker_schema(activated.conn)

    with critical_transaction(activated.conn):
        record_provider_production_success_in_transaction(activated.conn, now=NOW)
    metrics = read_provider_health_metrics(activated.conn)
    assert metrics.production_success_total == 1
    assert metrics.probe_success_total == 0
    assert metrics.probe_failure_total == 0

    _open_breaker(activated, policy=policy)
    with critical_transaction(activated.conn):
        record_provider_production_success_in_transaction(activated.conn, now=NOW)
    metrics_after_open = read_provider_health_metrics(activated.conn)
    assert metrics_after_open.production_success_total == 1


def test_fake_provider_canary_constant_matches_protocol() -> None:
    provider: JudgmentProvider = FakeProvider()
    result = provider.probe(PROVIDER_HEALTH_CANARY_PAYLOAD)
    assert result.success is True
