"""Tripwire: PolicyGate + metrics must be wired into process_alert_intake (Task 28a / DEC-048).

These tests are strict-xfail today. When integration lands, remove the markers or the
suite fails on XPASS — forcing explicit conversion to passing tests.
"""

from __future__ import annotations

import inspect

import pytest
from tests.policy.conftest import host_bundle

import praetor.engine.orchestrator as orchestrator_module
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.policy.containment_policy import NEVER_CONTAIN_SNAPSHOT

_XFAIL_REASON = (
    "DEC-048 / Task 28a: PolicyGate+metrics integration into "
    "process_alert_intake deferred to Phase 3; remove this marker when wired"
)


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_orchestrator_references_evaluate_policy_gate() -> None:
    """Structural guard: wiring is detected by symbol presence, not call-shape."""
    source = inspect.getsource(orchestrator_module)
    assert "evaluate_policy_gate" in source


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_intake_emits_auto_contain_when_gate_approves(
    activated,
) -> None:
    """Seed for Task 28a engine_intake eval (confirmed_malicious_sequence analog)."""
    judgment = skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN)
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-TRIPWIRE-AUTO-CONTAIN",
    )
    assert result.edict is not None
    assert result.disposition == Disposition.AUTO_CONTAIN
    assert result.edict.final_disposition == Disposition.AUTO_CONTAIN


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_intake_escalates_never_contain_snapshot_when_target_excluded(
    activated,
) -> None:
    """Seed for Task 28a engine_intake eval (never_contain_target analog).

    Mirrors ``evals/scenarios/never_contain_target.yaml``: host ``dc-01`` is on the
    snapshot never-contain list in ``configs/example_org.yaml``. Task 28a must pass a
    gate-approvable host bundle (see ``tests/policy/conftest.host_bundle``) into
    ``evaluate_policy_gate`` from the orchestrator path.
    """
    _ = host_bundle(host_id="dc-01")  # gate-approvable fixture reference for Task 28a
    judgment = skeleton_model_judgment(proposed=Disposition.AUTO_CONTAIN)
    provider = _CountingJudgmentProvider(judgment=judgment)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-TRIPWIRE-NEVER-CONTAIN",
    )
    assert result.edict is not None
    assert result.disposition == Disposition.ESCALATE
    assert NEVER_CONTAIN_SNAPSHOT in result.edict.fault_flags
