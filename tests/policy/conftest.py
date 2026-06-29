"""Pytest fixtures for policy gate tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.config.snapshot import compute_snapshot_hash_from_binding
from praetor.config.state import fetch_active_snapshot, persist_org_config_snapshot
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef, ModelJudgment
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.org_config_sections import ContainmentPolicy
from praetor.evidence.provenance import SYSMON_EVENT_LOG, WINDOWS_SECURITY_LOG
from praetor.state.store import StateStore, open_state_store

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


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


def _citable_field_path(fact: EvidenceFact) -> str:
    for key in ("process_name", "host_id", "target_sid", "account_name"):
        if key in fact.normalized_fields:
            return key
    return "process_name"


def host_bundle(*, host_id: str = "ws-01") -> EvidenceBundle:
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="ev-host-sysmon",
                normalized_fields={"host_id": host_id, "process_name": "cmd.exe"},
                source_event_reference="syn:host:sysmon:1",
                raw_source="{}",
                provenance_path=SYSMON_EVENT_LOG,
                ambiguity_flag=False,
                timestamp=NOW,
            ),
            EvidenceFact(
                evidence_id="ev-host-security",
                normalized_fields={"host_id": host_id, "event_id": 4624},
                source_event_reference="syn:host:security:1",
                raw_source="{}",
                provenance_path=WINDOWS_SECURITY_LOG,
                ambiguity_flag=False,
                timestamp=NOW,
            ),
        ]
    )


def default_auto_contain_citation_refs(
    bundle: EvidenceBundle,
) -> list[CitedEvidenceRef]:
    sysmon = next(
        (fact for fact in bundle.facts if fact.provenance_path == SYSMON_EVENT_LOG),
        None,
    )
    security = next(
        (
            fact
            for fact in bundle.facts
            if fact.provenance_path == WINDOWS_SECURITY_LOG
        ),
        None,
    )
    if sysmon is not None and security is not None:
        return [
            CitedEvidenceRef(
                evidence_id=sysmon.evidence_id,
                field_path=_citable_field_path(sysmon),
            ),
            CitedEvidenceRef(
                evidence_id=security.evidence_id,
                field_path=_citable_field_path(security),
            ),
        ]
    return [
        CitedEvidenceRef(
            evidence_id=bundle.facts[0].evidence_id,
            field_path=_citable_field_path(bundle.facts[0]),
        )
    ]


def account_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="syn-ev-sysmon",
                normalized_fields={
                    "process_name": "powershell.exe",
                    "user": "CORP\\jdoe",
                },
                source_event_reference="sysmon:1:1001",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=NOW,
            ),
            EvidenceFact(
                evidence_id="syn-ev-security",
                normalized_fields={
                    "account_name": "jdoe",
                    "target_sid": "S-1-5-21-1234567890-123456789-123456789-1001",
                    "domain": "CORP",
                },
                source_event_reference="security:4624:2001",
                raw_source="{}",
                provenance_path="windows_security_log",
                ambiguity_flag=False,
                timestamp=NOW,
            ),
        ]
    )


def auto_contain_judgment(
    bundle: EvidenceBundle,
    *,
    refs: list[CitedEvidenceRef] | None = None,
) -> ModelJudgment:
    if refs is None:
        refs = default_auto_contain_citation_refs(bundle)
    return ModelJudgment(
        proposed_disposition=Disposition.AUTO_CONTAIN,
        cited_evidence_refs=refs,
        key_tells=["test"],
        org_config_refs=["containment_policy.default_action"],
        benign_alternatives=[],
        benign_alternatives_ruled_out=[],
        convergence_reasoning="test",
        narrative="test",
        model_name="test",
        provider_name="test",
    )


def persist_snapshot_with_overrides(
    store: StateStore,
    base: OrgConfigSnapshot,
    **overrides: object,
) -> OrgConfigSnapshot:
    payload = base.model_dump(mode="json")
    for key, value in overrides.items():
        if hasattr(value, "model_dump"):
            payload[key] = value.model_dump(mode="json")
        else:
            payload[key] = value
    payload.pop("snapshot_hash", None)
    snapshot_hash = compute_snapshot_hash_from_binding(payload)
    updated = OrgConfigSnapshot.model_validate(
        {**payload, "snapshot_hash": snapshot_hash}
    )
    persist_org_config_snapshot(store.conn, updated, verbatim_render_text="policy-test")
    store.conn.execute(
        """
        UPDATE active_org_config
        SET snapshot_hash = ?, verbatim_render_id = ?
        WHERE id = 1
        """,
        (updated.snapshot_hash, "policy-test-render"),
    )
    store.conn.commit()
    return updated


def host_auto_contain_policy() -> ContainmentPolicy:
    """Permissive policy for tests that need gate auto_contain to succeed."""
    return ContainmentPolicy(
        default_action="auto_contain",
        rules=[],
    )


def permissive_org_snapshot(
    store: StateStore,
    base: OrgConfigSnapshot,
) -> OrgConfigSnapshot:
    return persist_snapshot_with_overrides(
        store,
        base,
        containment_policy=host_auto_contain_policy(),
    )
