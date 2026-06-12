"""Shared fixtures for containment lifecycle and revocation tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.containment import (
    ContainmentDirective,
    DirectiveStatus,
    TargetType,
)
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.hashing import compute_never_contain_entries_hash
from praetor.state.store import StateStore, open_state_store

NOW = datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC)


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


def sample_host_directive(
    *,
    directive_id: str = "dir-test-1",
    target_id: str = "dc-01",
    status: DirectiveStatus = DirectiveStatus.PROPOSED,
    minimum_feed_sequence: int = 0,
    issued_at: datetime | None = None,
) -> ContainmentDirective:
    issued = issued_at or datetime.now(UTC)
    return ContainmentDirective(
        directive_id=directive_id,
        decision_id="dec-test-1",
        target_type=TargetType.HOST,
        target_id=target_id,
        scope="host-isolation",
        evidence_refs=["ev-1"],
        issued_at=issued,
        expires_at=issued + timedelta(seconds=120),
        idempotency_key="idem-test-1",
        actuator_constraints={},
        revocation_policy={},
        status=status,
        live_never_contain_hash=compute_never_contain_entries_hash([]),
        embedded_never_contain_entries=[],
        minimum_feed_sequence_at_issue=minimum_feed_sequence,
    )
