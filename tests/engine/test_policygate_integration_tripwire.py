"""PolicyGate + metrics integration in process_alert_intake (Task 28a / DEC-048)."""

from __future__ import annotations

import inspect

from tests.policy.conftest import auto_contain_judgment, host_bundle

import praetor.engine.orchestrator as orchestrator_module
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.policy.containment_policy import NEVER_CONTAIN_SNAPSHOT


def test_orchestrator_references_evaluate_policy_gate() -> None:
    """Structural guard: wiring is detected by symbol presence, not call-shape."""
    source = inspect.getsource(orchestrator_module)
    assert "evaluate_policy_gate" in source


def test_intake_emits_auto_contain_when_gate_approves(
    activated,
) -> None:
    """Engine intake analog of confirmed_malicious_sequence."""
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-TRIPWIRE-AUTO-CONTAIN",
        evidence_bundle=bundle,
    )
    assert result.edict is not None
    assert result.disposition == Disposition.AUTO_CONTAIN
    assert result.edict.final_disposition == Disposition.AUTO_CONTAIN


def test_intake_escalates_never_contain_snapshot_when_target_excluded(
    activated,
) -> None:
    """Engine intake analog of never_contain_target (dc-01 on snapshot list)."""
    bundle = host_bundle(host_id="dc-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-TRIPWIRE-NEVER-CONTAIN",
        evidence_bundle=bundle,
    )
    assert result.edict is not None
    assert result.disposition == Disposition.ESCALATE
    assert NEVER_CONTAIN_SNAPSHOT in result.edict.fault_flags
