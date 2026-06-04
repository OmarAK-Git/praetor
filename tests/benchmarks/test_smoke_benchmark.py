"""Task 11 — smoke serialized-path benchmark."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from benchmarks.smoke_serialized_path import (
    SmokeBenchmarkResult,
    provisional_targets_from_conn,
    run_smoke_for_store,
    run_smoke_serialized_path_benchmark,
)
from tests.config.shared import EXAMPLE_CONFIG, REPO_ROOT, SOC_LEAD_TOKEN

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.state.store import StateStore, open_state_store


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
    yield store
    store.close()


def test_smoke_benchmark_uses_active_org_config_targets(
    activated_store: StateStore,
) -> None:
    sustained, burst = provisional_targets_from_conn(activated_store.conn)
    assert sustained == 30
    assert burst == 60
    result = run_smoke_for_store(activated_store, operations=5)
    assert isinstance(result, SmokeBenchmarkResult)
    assert result.target_sustained == 30
    assert result.target_burst == 60
    assert result.operations == 5
    assert result.elapsed_seconds > 0
    assert result.sustained_alerts_per_minute > 0


def test_smoke_benchmark_module_entry_uses_active_config(
    tmp_path: Path, verifier: PrincipalMapVerifier
) -> None:
    db = tmp_path / "bench.db"
    store = open_state_store(db)
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    store.close()

    custom_config = REPO_ROOT / "configs" / "example_org.yaml"
    data = yaml.safe_load(custom_config.read_text(encoding="utf-8"))
    data["provisional_alert_rate_targets"] = {
        "sustained_alerts_per_minute": 17,
        "burst_alerts_per_minute": 42,
    }
    custom_path = tmp_path / "custom_org.yaml"
    custom_path.write_text(yaml.dump(data), encoding="utf-8")

    store2 = open_state_store(tmp_path / "custom.db")
    activate_org_config(store2, custom_path, token=SOC_LEAD_TOKEN, verifier=verifier)
    store2.close()

    result = run_smoke_serialized_path_benchmark(tmp_path / "custom.db", operations=3)
    assert result.target_sustained == 17
    assert result.target_burst == 42
    assert result.operations == 3
