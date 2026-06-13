"""TASK-022 latency SLA and queue aging."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from tests.config.shared import EXAMPLE_SNAPSHOT_HASH
from tests.engine.helpers import assert_outcome_matrix_edict, fetch_ledger_edicts

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.orchestrator import process_alert_intake
from praetor.engine.queue_policy import (
    attempt_queue_age_seconds,
    queue_aging_exceeded,
    queue_aging_exceeded_for_snapshot,
)
from praetor.engine.recovery import recover_single_attempt, run_engine_startup_recovery
from praetor.engine.skeleton import SKELETON_BUNDLE_HASH, skeleton_model_judgment
from praetor.engine.timeouts import (
    TrackedProviderCall,
    call_provider_with_latency_tracking,
    provider_latency_sla_exceeded,
)
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderRetryPolicy,
    ProviderTimeoutError,
)
from praetor.policy.gate import LATENCY_SLA_EXCEEDED, QUEUE_AGING_EXCEEDED
from praetor.state.attempts import (
    AttemptState,
    ProcessingAttempt,
    fetch_all_non_terminal_attempts,
    transition_attempt,
)


class _SlowJudgmentProvider:
    delay_seconds: float = 0.05

    def __init__(self, *, proposed: Disposition = Disposition.STANDARD_REVIEW) -> None:
        self.proposed = proposed
        self.calls = 0

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        _ = request
        self.calls += 1
        time.sleep(self.delay_seconds)
        return skeleton_model_judgment(proposed=self.proposed)

    def probe(self, canary_payload: object) -> object:
        _ = canary_payload
        raise NotImplementedError


class _TimeoutThenSucceedProvider:
    def __init__(self, clock: list[float]) -> None:
        self.clock = clock
        self.calls = 0

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        _ = request
        self.calls += 1
        if self.calls == 1:
            self.clock[0] += 20.0
            raise ProviderTimeoutError("first attempt timed out")
        self.clock[0] += 10.0
        return skeleton_model_judgment()


def _backdate_attempt(
    conn,
    processing_attempt_identity: str,
    *,
    created_at: datetime,
) -> None:
    conn.execute(
        """
        UPDATE processing_attempts
        SET created_at = ?, updated_at = ?
        WHERE attempt_id = ?
        """,
        (
            created_at.isoformat(),
            created_at.isoformat(),
            int(processing_attempt_identity),
        ),
    )
    conn.commit()


def _count_outstanding_directives(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM outstanding_containment_directives WHERE revoked = 0"
    ).fetchone()
    assert row is not None
    return int(row["c"])


def test_provider_latency_sla_exceeded_boundary() -> None:
    assert provider_latency_sla_exceeded(30.0, max_latency_seconds=30) is False
    assert provider_latency_sla_exceeded(30.001, max_latency_seconds=30) is True


def test_queue_aging_exceeded_boundary() -> None:
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    at_max = ProcessingAttempt(
        processing_attempt_identity="1",
        alert_identity="ALERT-BOUNDARY",
        evidence_bundle_hash="hash",
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
        state=AttemptState.ACTIVE,
        created_at=now - timedelta(seconds=120),
        updated_at=now - timedelta(seconds=120),
    )
    over_max = ProcessingAttempt(
        processing_attempt_identity="2",
        alert_identity="ALERT-BOUNDARY-2",
        evidence_bundle_hash="hash",
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
        state=AttemptState.ACTIVE,
        created_at=now - timedelta(seconds=120, milliseconds=1),
        updated_at=now - timedelta(seconds=120, milliseconds=1),
    )
    assert queue_aging_exceeded(at_max, max_age_seconds=120, now=now) is False
    assert queue_aging_exceeded(over_max, max_age_seconds=120, now=now) is True


def test_call_provider_with_latency_tracking_uses_monotonic(
    judgment_provider,
) -> None:
    times = iter([0.0, 45.0])

    def fake_monotonic() -> float:
        return next(times)

    tracked = call_provider_with_latency_tracking(
        judgment_provider,
        JudgmentRequest(scenario_id="latency-unit", payload={}),
        max_latency_seconds=30,
        monotonic=fake_monotonic,
    )
    assert tracked.elapsed_seconds == 45.0
    assert tracked.sla_exceeded is True


def test_cumulative_retry_latency_includes_backoff_and_attempts() -> None:
    clock = [0.0]

    def monotonic() -> float:
        return clock[0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    provider = _TimeoutThenSucceedProvider(clock)
    tracked = call_provider_with_latency_tracking(
        provider,
        JudgmentRequest(scenario_id="retry-latency", payload={}),
        retry_policy=ProviderRetryPolicy(max_attempts=2, backoff_seconds=5.0),
        max_latency_seconds=30,
        sleep=sleep,
        monotonic=monotonic,
    )
    assert provider.calls == 2
    assert tracked.elapsed_seconds == pytest.approx(35.0)
    assert tracked.sla_exceeded is True


def test_cumulative_retry_latency_under_sla_when_total_time_ok() -> None:
    clock = [0.0]

    def monotonic() -> float:
        return clock[0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    class _FastRetryProvider:
        def __init__(self) -> None:
            self.calls = 0

        def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
            _ = request
            self.calls += 1
            if self.calls == 1:
                clock[0] += 5.0
                raise ProviderTimeoutError("retry")
            clock[0] += 5.0
            return skeleton_model_judgment()

    tracked = call_provider_with_latency_tracking(
        _FastRetryProvider(),
        JudgmentRequest(scenario_id="retry-under-sla", payload={}),
        retry_policy=ProviderRetryPolicy(max_attempts=2, backoff_seconds=2.0),
        max_latency_seconds=30,
        sleep=sleep,
        monotonic=monotonic,
    )
    assert tracked.elapsed_seconds == pytest.approx(12.0)
    assert tracked.sla_exceeded is False


def test_provider_latency_beyond_sla_escalates(
    activated,
    stamp_backend,
) -> None:
    provider = _SlowJudgmentProvider()
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-LATENCY-SLA",
        max_provider_latency_seconds=0,
    )
    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=[LATENCY_SLA_EXCEEDED],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert provider.calls == 1
    assert result.judgment_provider_calls == 1


def test_slow_auto_contain_proposal_latency_sla_blocks_containment(
    activated,
    stamp_backend,
) -> None:
    provider = _SlowJudgmentProvider(proposed=Disposition.AUTO_CONTAIN)
    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=stamp_backend,
        alert_identity="ALERT-LATENCY-AUTO-CONTAIN",
        max_provider_latency_seconds=0,
    )
    assert result.edict is not None
    assert result.disposition == Disposition.ESCALATE
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=[LATENCY_SLA_EXCEEDED],
        system_fault_escalation=True,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )
    assert _count_outstanding_directives(activated.conn) == 0
    assert provider.calls == 1


def test_queue_aging_helpers_use_snapshot_policy(activated) -> None:
    from praetor.config.state import fetch_active_snapshot

    snapshot = fetch_active_snapshot(activated.conn)
    assert snapshot is not None
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    attempt = ProcessingAttempt(
        processing_attempt_identity="1",
        alert_identity="ALERT-HELPER",
        evidence_bundle_hash="hash",
        org_config_snapshot_hash=snapshot.snapshot_hash,
        state=AttemptState.ACTIVE,
        created_at=now - timedelta(seconds=121),
        updated_at=now - timedelta(seconds=121),
    )
    assert attempt_queue_age_seconds(attempt, now=now) == pytest.approx(121.0)
    assert queue_aging_exceeded(attempt, max_age_seconds=120, now=now) is True
    assert queue_aging_exceeded_for_snapshot(attempt, snapshot, now=now) is True


def test_aged_non_terminal_recovery_emits_queue_aging(
    activated,
    stamp_backend,
) -> None:
    stale_created = datetime.now(UTC) - timedelta(seconds=200)
    cur = activated.conn.execute(
        """
        INSERT INTO processing_attempts (
            alert_identity, evidence_bundle_hash, org_config_snapshot_hash,
            state, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "ALERT-STALE-RECOVERY",
            "bundle-hash",
            EXAMPLE_SNAPSHOT_HASH,
            AttemptState.ACTIVE.value,
            stale_created.isoformat(),
            stale_created.isoformat(),
        ),
    )
    activated.conn.commit()
    attempt_id = str(cur.lastrowid)
    from praetor.state.attempts import _fetch_attempt_by_id

    attempt = _fetch_attempt_by_id(activated.conn, attempt_id)
    assert attempt is not None
    recover_single_attempt(activated, attempt, stamp_backend)
    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert_outcome_matrix_edict(
        edicts[0],
        final_disposition=Disposition.ESCALATE,
        fault_flags=[QUEUE_AGING_EXCEEDED],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert fetch_all_non_terminal_attempts(activated.conn) == []


def test_aged_pending_stamp_resolves_via_stamp_not_queue_aging(
    activated,
    stamp_backend,
) -> None:
    stale_created = datetime.now(UTC) - timedelta(seconds=200)
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-STALE-PENDING-STAMP",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)
    _backdate_attempt(activated.conn, aid, created_at=stale_created)

    from praetor.state.attempts import _fetch_attempt_by_id

    attempt = _fetch_attempt_by_id(activated.conn, aid)
    assert attempt is not None
    recover_single_attempt(activated, attempt, stamp_backend)

    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert QUEUE_AGING_EXCEEDED not in edicts[0].fault_flags
    assert edicts[0].final_disposition == Disposition.STANDARD_REVIEW
    assert fetch_all_non_terminal_attempts(activated.conn) == []


def test_aged_stamp_resolved_completes_without_queue_aging(
    activated,
    stamp_backend,
) -> None:
    stale_created = datetime.now(UTC) - timedelta(seconds=200)
    alloc = activated.allocate_attempt(
        alert_identity="ALERT-STALE-STAMP-RESOLVED",
        evidence_bundle_hash=SKELETON_BUNDLE_HASH,
        org_config_snapshot_hash=EXAMPLE_SNAPSHOT_HASH,
    )
    assert alloc.attempt is not None
    aid = alloc.attempt.processing_attempt_identity
    transition_attempt(activated.conn, aid, AttemptState.ACTIVE)
    transition_attempt(activated.conn, aid, AttemptState.PENDING_STAMP)

    from praetor.tickets.stamp import StampContext, execute_stamp

    execute_stamp(
        activated.conn,
        stamp_backend,
        StampContext(
            alert_identity=alloc.attempt.alert_identity,
            evidence_bundle_hash=alloc.attempt.evidence_bundle_hash,
            org_config_snapshot_hash=alloc.attempt.org_config_snapshot_hash,
            processing_attempt_identity=aid,
            ticket_payload={
                "candidate_judgment": skeleton_model_judgment().model_dump(mode="json"),
            },
        ),
    )
    transition_attempt(activated.conn, aid, AttemptState.STAMP_RESOLVED)
    _backdate_attempt(activated.conn, aid, created_at=stale_created)

    from praetor.state.attempts import _fetch_attempt_by_id

    attempt = _fetch_attempt_by_id(activated.conn, aid)
    assert attempt is not None
    recover_single_attempt(activated, attempt, stamp_backend)

    edicts = fetch_ledger_edicts(activated.conn)
    assert len(edicts) == 1
    assert QUEUE_AGING_EXCEEDED not in edicts[0].fault_flags
    assert fetch_all_non_terminal_attempts(activated.conn) == []


def test_startup_recovery_escalates_aged_active_attempt(
    activated,
    stamp_backend,
) -> None:
    stale_created = datetime.now(UTC) - timedelta(seconds=200)
    activated.conn.execute(
        """
        INSERT INTO processing_attempts (
            alert_identity, evidence_bundle_hash, org_config_snapshot_hash,
            state, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "ALERT-STARTUP-STALE",
            "bundle-hash",
            EXAMPLE_SNAPSHOT_HASH,
            AttemptState.ALLOCATED.value,
            stale_created.isoformat(),
            stale_created.isoformat(),
        ),
    )
    activated.conn.commit()
    run_engine_startup_recovery(activated, stamp_backend=stamp_backend)
    assert len(fetch_ledger_edicts(activated.conn)) == 1
    assert fetch_all_non_terminal_attempts(activated.conn) == []


def test_latency_and_queue_fault_flags_are_distinct() -> None:
    assert LATENCY_SLA_EXCEEDED != QUEUE_AGING_EXCEEDED


def test_tracked_provider_call_marks_sla_exceeded() -> None:
    tracked = TrackedProviderCall(
        judgment=skeleton_model_judgment(),
        elapsed_seconds=31.0,
        sla_exceeded=True,
    )
    assert tracked.sla_exceeded is True
