"""Gate target ownership on intake (V2-015 / AG-0080)."""

from __future__ import annotations

import ast
import inspect
import json
from datetime import UTC, datetime

import pytest
from evals.correlation_gate import REPO_ROOT, load_correlation_expected
from evals.run_phase3_gate import INCIDENT_HOST_ID, REQUIRED_EXPECTED_PATH
from tests.policy.conftest import (
    auto_contain_judgment,
    host_auto_contain_policy,
    permissive_org_snapshot,
    persist_snapshot_with_overrides,
)

import praetor.engine.orchestrator as orchestrator_module
from praetor.config.state import fetch_active_snapshot
from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.policy.gate import gate_resolved_containment_target
from praetor.policy.identity import INSUFFICIENT_CORROBORATION

_FORBIDDEN_TARGET_RESOLVERS = frozenset(
    {
        "resolve_containment_target",
        "resolve_host_target_from_citations",
    }
)


def _orchestrator_forbidden_target_resolver_names() -> set[str]:
    source = inspect.getsource(orchestrator_module)
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_TARGET_RESOLVERS:
            found.add(node.id)
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_TARGET_RESOLVERS:
            found.add(node.attr)
    return found


def test_orchestrator_forbids_bundle_target_rederivation() -> None:
    """Static guard: intake must not resolve containment targets from bundle facts."""
    forbidden = _orchestrator_forbidden_target_resolver_names()
    assert forbidden == set()
    source = inspect.getsource(orchestrator_module)
    assert "gate_resolved_containment_target" in source


def test_gate_resolved_containment_target_rejects_missing_target() -> None:
    from praetor.policy.gate import PolicyGateEvaluation

    evaluation = PolicyGateEvaluation(
        proposed_disposition=Disposition.AUTO_CONTAIN,
        final_disposition=Disposition.AUTO_CONTAIN,
        fault_flags=[],
        system_fault_escalation=False,
    )
    with pytest.raises(RuntimeError, match="missing resolved containment target"):
        gate_resolved_containment_target(evaluation)


def _sysmon_only_noisy_bundle():
    scenario = load_correlation_expected(REQUIRED_EXPECTED_PATH)
    inputs = scenario.inputs
    anchor_time = datetime.fromisoformat(
        str(inputs.get("anchor_time")).replace("Z", "+00:00")
    )
    window_seconds = int(inputs.get("window_seconds", 300))
    sysmon_events: list[dict] = []
    for path_value in inputs.get("sysmon_fixtures") or []:
        fixture_path = REPO_ROOT / str(path_value)
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        sysmon_events.extend(load_fixture_events(payload))
    return correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=[],
        anchor_time=anchor_time,
        window_seconds=window_seconds,
    ).bundle


def _two_host_bundle_with_uncited_noise() -> EvidenceBundle:
    ts = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    return EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="host-a-1",
                normalized_fields={
                    "host_id": "WORKSTATION1",
                    "process_name": "cmd.exe",
                },
                source_event_reference="syn:a:1",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
            EvidenceFact(
                evidence_id="host-a-2",
                normalized_fields={
                    "host_id": "WORKSTATION1",
                    "event_id": 4624,
                },
                source_event_reference="syn:a:2",
                raw_source="{}",
                provenance_path="windows_security_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
            EvidenceFact(
                evidence_id="host-b-1",
                normalized_fields={
                    "host_id": "WORKSTATION2",
                    "process_name": "notepad.exe",
                },
                source_event_reference="syn:b:1",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=False,
                timestamp=ts,
            ),
        ]
    )


def test_intake_two_host_bundle_persists_only_cited_gate_target(
    activated,
) -> None:
    """Uncited WORKSTATION2 in bundle cannot steer persisted directive target."""
    org_snapshot = fetch_active_snapshot(activated.conn)
    assert org_snapshot is not None
    bundle = _two_host_bundle_with_uncited_noise()
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(evidence_id="host-a-1", field_path="host_id"),
            CitedEvidenceRef(evidence_id="host-a-2", field_path="host_id"),
        ],
    )
    snapshot = permissive_org_snapshot(activated, org_snapshot, "WORKSTATION1")
    _ = snapshot
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-INTAKE-TWO-HOST-NOISE",
        evidence_bundle=bundle,
    )
    assert result.edict is not None
    assert result.disposition == Disposition.AUTO_CONTAIN
    assert result.edict.policy_gate_result.final_disposition == Disposition.AUTO_CONTAIN
    directive_row = activated.conn.execute(
        """
        SELECT directive_json FROM outstanding_containment_directives
        WHERE revoked = 0
        ORDER BY rowid DESC LIMIT 1
        """
    ).fetchone()
    assert directive_row is not None
    directive = json.loads(directive_row["directive_json"])
    assert directive["target_id"] == "WORKSTATION1"
    assert directive["target_id"] != "WORKSTATION2"
    host_ids = {
        fact.normalized_fields.get("host_id")
        for fact in bundle.facts
        if fact.normalized_fields.get("host_id")
    }
    assert host_ids == {"WORKSTATION1", "WORKSTATION2"}


def test_intake_insufficient_corroboration_does_not_persist_directive(
    activated,
) -> None:
    """Sole ambiguous host citation escalates without persisting directive."""
    org_snapshot = fetch_active_snapshot(activated.conn)
    assert org_snapshot is not None
    ts = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)
    bundle = EvidenceBundle(
        facts=[
            EvidenceFact(
                evidence_id="host-ambiguous-only",
                normalized_fields={
                    "host_id": INCIDENT_HOST_ID,
                    "process_name": "cmd.exe",
                },
                source_event_reference="syn:amb:intake",
                raw_source="{}",
                provenance_path="sysmon_event_log",
                ambiguity_flag=True,
                timestamp=ts,
            ),
        ]
    )
    judgment = auto_contain_judgment(
        bundle,
        refs=[
            CitedEvidenceRef(
                evidence_id="host-ambiguous-only",
                field_path="host_id",
            )
        ],
    )
    snapshot = permissive_org_snapshot(activated, org_snapshot, INCIDENT_HOST_ID)
    _ = snapshot
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-INTAKE-SOLE-AMB",
        evidence_bundle=bundle,
    )
    assert result.edict is not None
    assert result.disposition == Disposition.ESCALATE
    assert INSUFFICIENT_CORROBORATION in result.fault_flags
    row = activated.conn.execute(
        "SELECT COUNT(*) AS c FROM outstanding_containment_directives WHERE revoked = 0"
    ).fetchone()
    assert row is not None
    assert int(row["c"]) == 0


def test_intake_persists_gate_resolved_target_on_auto_contain(activated) -> None:
    """Happy path: persisted directive target matches gate resolved_target."""
    from tests.policy.conftest import host_bundle

    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    persist_snapshot_with_overrides(
        activated,
        snapshot,
        containment_policy=host_auto_contain_policy("ws-01"),
    )
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-INTAKE-GATE-TARGET",
        evidence_bundle=bundle,
    )
    assert result.edict is not None
    assert result.disposition == Disposition.AUTO_CONTAIN
    directive_row = activated.conn.execute(
        """
        SELECT directive_json FROM outstanding_containment_directives
        WHERE revoked = 0
        ORDER BY rowid DESC LIMIT 1
        """
    ).fetchone()
    assert directive_row is not None
    directive = json.loads(directive_row["directive_json"])
    assert directive["target_id"] == "ws-01"
