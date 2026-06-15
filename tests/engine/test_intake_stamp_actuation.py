"""Intake stamp ordering: directive durability deferred until terminal stamp (Task 28a)."""

from __future__ import annotations

from tests.config.shared import SOC_LEAD_TOKEN
from tests.engine.helpers import assert_outcome_matrix_edict
from tests.engine.stamp_fakes import (
    AlwaysFailedStampBackend,
    AlwaysTimeoutStampBackend,
    InjectNeverContainOnStampBackend,
)
from tests.policy.conftest import auto_contain_judgment, host_bundle

from praetor.config.emergency import add_emergency_never_contain
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import (
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.policy.containment_policy import NEVER_CONTAIN_LIVE_CONFLICT
from praetor.tickets.contract import TICKET_STAMP_FAILED


def _outstanding_directive_count(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM outstanding_containment_directives WHERE revoked = 0"
    ).fetchone()
    assert row is not None
    return int(row["c"])


def test_unknown_stamp_leaves_no_outstanding_directive_for_auto_contain(
    activated,
) -> None:
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AlwaysTimeoutStampBackend(),
        alert_identity="ALERT-UNKNOWN-STAMP",
        evidence_bundle=bundle,
    )

    assert result.edict is None
    assert _outstanding_directive_count(activated.conn) == 0


def test_pending_stamp_backend_leaves_no_outstanding_directive(
    activated,
) -> None:
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AlwaysTimeoutStampBackend(),
        alert_identity="ALERT-PENDING-STAMP",
        evidence_bundle=bundle,
    )

    assert result.edict is None
    assert _outstanding_directive_count(activated.conn) == 0


def test_failed_stamp_auto_contain_emits_directive_and_preserves_candidate(
    activated,
) -> None:
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=AlwaysFailedStampBackend(),
        alert_identity="ALERT-FAIL-AC-INTAKE",
        evidence_bundle=bundle,
    )

    assert result.edict is not None
    assert _outstanding_directive_count(activated.conn) == 1
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.AUTO_CONTAIN,
        fault_flags=[TICKET_STAMP_FAILED],
        system_fault_escalation=False,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )


def test_deferred_persist_never_contain_conflict_escalates_in_band(
    activated,
    verifier,
) -> None:
    """Live never-contain added after gate eval but before deferred persist."""
    bundle = host_bundle(host_id="ws-01")
    judgment = auto_contain_judgment(bundle)
    provider = _CountingJudgmentProvider(judgment=judgment)

    def inject_live_never_contain() -> None:
        add_emergency_never_contain(
            activated,
            token=SOC_LEAD_TOKEN,
            verifier=verifier,
            target_specification={"target_type": "host", "target_id": "ws-01"},
            lifetime_seconds=3600,
            audit_reason="mid-stamp hold",
        )

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=InjectNeverContainOnStampBackend(on_stamp=inject_live_never_contain),
        alert_identity="ALERT-DEFERRED-NC-CONFLICT",
        evidence_bundle=bundle,
    )

    assert result.edict is not None
    assert _outstanding_directive_count(activated.conn) == 0
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=[NEVER_CONTAIN_LIVE_CONFLICT],
        system_fault_escalation=False,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )
