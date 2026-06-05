"""TASK-012 walking skeleton decision flow."""

from __future__ import annotations

from unittest.mock import patch

from tests.config.shared import EXAMPLE_SNAPSHOT_HASH
from tests.engine.helpers import (
    assert_edict_snapshot_pairing,
    assert_outcome_matrix_edict,
    count_ledger_records,
    fetch_ledger_edicts,
)

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import CitedEvidenceRef
from praetor.engine.orchestrator import (
    WalkingSkeletonEngine,
    _CountingJudgmentProvider,
    process_alert_intake,
)
from praetor.engine.skeleton import (
    SKELETON_BUNDLE_HASH,
    SKELETON_EVIDENCE_ID,
    skeleton_model_judgment,
)
from praetor.hashing import EMPTY_BUNDLE
from praetor.state.attempts import fetch_all_non_terminal_attempts


def test_hardcoded_bundle_produces_valid_decision_edict(
    activated,
    stamp_backend,
    judgment_provider,
) -> None:
    engine = WalkingSkeletonEngine(
        store=activated,
        judgment_provider=judgment_provider,
        stamp_backend=stamp_backend,
    )
    result = engine.process_intake()
    assert result.edict is not None
    assert result.disposition == Disposition.STANDARD_REVIEW
    assert result.edict.record_type == "decision_edict"
    assert result.edict.evidence_bundle_hash == SKELETON_BUNDLE_HASH
    assert result.edict.org_config_snapshot_hash == EXAMPLE_SNAPSHOT_HASH
    assert result.edict.ticket_stamp_payload

    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert_edict_snapshot_pairing(activated.conn, edicts[0])
    assert count_ledger_records(activated.conn, "never_contain_snapshot") == 1
    assert fetch_all_non_terminal_attempts(activated.conn) == []


def test_correlation_failure_escalates_with_empty_bundle_and_aborts(
    activated,
    stamp_backend,
    judgment_provider,
) -> None:
    result = process_alert_intake(
        activated,
        judgment_provider=judgment_provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-CORR-2",
        correlate=False,
    )
    assert result.attempt_aborted is True
    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["correlation_failure"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.ESCALATE,
    )
    assert result.edict.evidence_bundle_hash == EMPTY_BUNDLE
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_config_over_budget_escalates_without_judgment_provider_call(
    activated,
    stamp_backend,
) -> None:
    provider = _CountingJudgmentProvider(judgment=skeleton_model_judgment())
    huge = "x" * 500_000
    with patch(
        "praetor.engine.orchestrator.fetch_verbatim_render_text",
        return_value=huge,
    ):
        result = process_alert_intake(
            activated,
            judgment_provider=provider,
            stamp_backend=stamp_backend,
            alert_identity="ALERT-BUDGET",
        )
    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["config_over_budget"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert provider.calls == 0
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_invalid_citation_escalates(
    activated,
    stamp_backend,
) -> None:
    bad = skeleton_model_judgment(
        cited_refs=[
            CitedEvidenceRef(evidence_id="missing-ev", field_path="process_name"),
        ],
    )
    provider = _CountingJudgmentProvider(judgment=bad)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-BAD-CITE",
    )
    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["invalid_model_citation"],
        system_fault_escalation=True,
        proposed_disposition=bad.proposed_disposition,
    )
    assert provider.calls == 1
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_ticket_stamp_payload_present_on_happy_path(
    activated,
    stamp_backend,
    judgment_provider,
) -> None:
    result = process_alert_intake(
        activated,
        judgment_provider=judgment_provider,
        stamp_backend=stamp_backend,
    )
    assert result.edict is not None
    assert result.edict.stamp_status == "succeeded"
    assert result.edict.ticket_stamp_payload
    cited = result.edict.ticket_stamp_payload.get("candidate_judgment", {})
    refs = cited.get("cited_evidence_refs", [])
    assert any(r.get("evidence_id") == SKELETON_EVIDENCE_ID for r in refs)
