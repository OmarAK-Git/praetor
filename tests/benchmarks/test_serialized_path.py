"""Task 35 — production serialized-path benchmark (DEC-053 faithful)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import benchmarks.serialized_path as serialized_path_module
import pytest
from benchmarks.serialized_path import (
    BURST_SEPARATELY_MEASURED_V1,
    PRODUCTION_MEASURED_SUBSYSTEMS,
    PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION,
    BenchmarkMeasurementContext,
    SerializedPathBenchmarkResult,
    benchmark_result_from_timing,
    collect_benchmark_measurement_context,
    run_contended_production_path_pair,
    run_one_production_serialized_path_operation,
    run_one_serialized_path_operation,
    run_serialized_path_benchmark,
    run_serialized_path_for_store,
)
from benchmarks.smoke_serialized_path import provisional_targets_from_conn
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN
from tests.policy.conftest import (
    auto_contain_default_policy,
    persist_snapshot_with_overrides,
)

import praetor.policy.gate as policy_gate_module
import praetor.state.sqlite_guard as sqlite_guard_module
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.state import fetch_active_snapshot
from praetor.hashing import derive_idempotency_key
from praetor.ledger.store import fetch_ledger_rows
from praetor.revocation.outbox import list_pending_feed_outbox_rows
from praetor.state.idempotency import fetch_active_idempotency_key
from praetor.state.store import StateStore, open_state_store

NOW = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )


@pytest.fixture
def activated_store(
    tmp_path: Path, verifier: PrincipalMapVerifier
) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    store = open_state_store(db)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    snapshot = fetch_active_snapshot(store.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        store, snapshot, containment_policy=auto_contain_default_policy()
    )
    yield store
    store.close()


def test_serialized_path_benchmark_uses_active_org_config_targets(
    activated_store: StateStore,
) -> None:
    sustained, burst = provisional_targets_from_conn(activated_store.conn)
    assert sustained == 30
    assert burst == 60
    result = run_serialized_path_for_store(activated_store, operations=3)
    assert isinstance(result, SerializedPathBenchmarkResult)
    assert result.target_sustained == 30
    assert result.target_burst == 60
    assert result.operations == 3
    assert result.elapsed_seconds > 0
    assert result.sustained_alerts_per_minute > 0
    assert result.burst_separately_measured is False


def test_benchmark_result_always_emits_measurement_context(
    activated_store: StateStore,
) -> None:
    result = run_serialized_path_for_store(activated_store, operations=2)
    context = result.measurement_context
    assert isinstance(context, BenchmarkMeasurementContext)
    assert context.scenario == "uncontended_distinct_host"
    assert context.informational_only is True
    assert context.platform
    assert context.machine
    assert context.python_version


def test_benchmark_measurement_context_hardware_fields_present() -> None:
    context = collect_benchmark_measurement_context()
    assert context.processor
    assert context.cpu_count is None or context.cpu_count >= 1


def test_benchmark_burst_not_measured_in_separate_window() -> None:
    result = benchmark_result_from_timing(
        operations=60,
        elapsed=1.0,
        target_sustained=30,
        target_burst=60,
    )
    assert result.burst_separately_measured is False
    assert result.meets_burst_target_informational is True
    assert not hasattr(result, "burst_alerts_per_minute")


def test_benchmark_target_comparison_semantics() -> None:
    above = benchmark_result_from_timing(
        operations=60,
        elapsed=1.0,
        target_sustained=30,
        target_burst=60,
    )
    assert above.meets_sustained_target is True
    assert above.meets_burst_target_informational is True

    below = benchmark_result_from_timing(
        operations=1,
        elapsed=60.0,
        target_sustained=30,
        target_burst=60,
    )
    assert below.meets_sustained_target is False
    assert below.meets_burst_target_informational is False
    assert below.burst_separately_measured is BURST_SEPARATELY_MEASURED_V1


def test_production_path_transaction_structure(
    activated_store: StateStore,
) -> None:
    snapshot = fetch_active_snapshot(activated_store.conn)
    assert snapshot is not None
    conn = activated_store.conn
    begin_count = 0
    real_critical = sqlite_guard_module.critical_transaction

    @contextmanager
    def counting_critical(connection: object) -> Iterator[object]:
        nonlocal begin_count
        begin_count += 1
        with real_critical(connection) as active:  # type: ignore[arg-type]
            yield active

    pending_before = len(list_pending_feed_outbox_rows(conn))
    with (
        patch.object(policy_gate_module, "critical_transaction", counting_critical),
        patch.object(serialized_path_module, "critical_transaction", counting_critical),
    ):
        run_one_production_serialized_path_operation(
            activated_store, snapshot, index=0, moment=NOW
        )

    assert begin_count == PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION
    assert len(list_pending_feed_outbox_rows(conn)) == pending_before


def test_benchmark_iteration_write_set_uncontended(
    activated_store: StateStore,
) -> None:
    snapshot = fetch_active_snapshot(activated_store.conn)
    assert snapshot is not None
    ledger_before = len(fetch_ledger_rows(activated_store.conn))
    pending_before = len(list_pending_feed_outbox_rows(activated_store.conn))

    evaluation = run_one_serialized_path_operation(
        activated_store, snapshot, index=0, moment=NOW
    )
    assert evaluation.directive_suppressed is False

    ledger_after = len(fetch_ledger_rows(activated_store.conn))
    pending_after = len(list_pending_feed_outbox_rows(activated_store.conn))
    assert ledger_after == ledger_before + 2
    assert pending_after == pending_before

    idem_key = derive_idempotency_key(
        "BENCH-000000",
        "host",
        "ws-bench-000000",
        "host-isolation",
    )
    assert fetch_active_idempotency_key(activated_store.conn, idem_key) is not None
    from praetor.policy.rate_limit import rate_limit_scope_key
    from praetor.policy.state import read_rate_counter

    scope_key = rate_limit_scope_key(
        "per_host",
        target_type="host",
        target_id="ws-bench-000000",
    )
    assert read_rate_counter(activated_store.conn, scope_key) == 1
    assert len(PRODUCTION_MEASURED_SUBSYSTEMS) == 8


def test_contended_path_suppresses_second_directive_emission(
    activated_store: StateStore,
) -> None:
    snapshot = fetch_active_snapshot(activated_store.conn)
    assert snapshot is not None
    first, second = run_contended_production_path_pair(
        activated_store, snapshot, moment=NOW
    )
    assert first.directive_suppressed is False
    assert second.directive_suppressed is True
    assert first.containment_directive is not None
    assert second.containment_directive is not None
    assert (
        first.containment_directive.directive_id
        == second.containment_directive.directive_id
    )
    row = activated_store.conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM outstanding_containment_directives
        WHERE target_id = ?
        """,
        ("ws-contended",),
    ).fetchone()
    assert row is not None
    assert int(row["count"]) == 1


def test_recorded_sample_run_meets_example_org_sustained_target(
    activated_store: StateStore,
) -> None:
    """Pins a committed sample rate; update if benchmark path changes materially."""
    result = run_serialized_path_for_store(activated_store, operations=10)
    sample = benchmark_result_from_timing(
        operations=result.operations,
        elapsed=result.elapsed_seconds,
        target_sustained=result.target_sustained,
        target_burst=result.target_burst,
    )
    assert sample.meets_sustained_target is True
    assert sample.sustained_alerts_per_minute >= float(sample.target_sustained)


def test_serialized_path_module_entry_uses_active_config(
    tmp_path: Path, verifier: PrincipalMapVerifier
) -> None:
    db = tmp_path / "bench.db"
    store = open_state_store(db)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    snapshot = fetch_active_snapshot(store.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        store, snapshot, containment_policy=auto_contain_default_policy()
    )
    store.close()

    result = run_serialized_path_benchmark(db, operations=2)
    assert result.operations == 2
    assert result.target_sustained == 30
    assert result.target_burst == 60
