"""Fixtures for correlation identity compliance tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.state.store import StateStore, open_state_store


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
def org_snapshot(activated: StateStore) -> OrgConfigSnapshot:
    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    return snapshot
