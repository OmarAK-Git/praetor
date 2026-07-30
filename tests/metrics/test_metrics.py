"""TASK-024 metrics collector tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from praetor.alerts.outbox import V1_DELIVERY_CHANNELS, DeliveryStatus
from praetor.contracts.disposition import Disposition
from praetor.metrics.collector import MetricsCollector, compute_p99
from praetor.metrics.events import (
    DEFAULT_FEED_LAG_SAMPLE_WINDOW,
    TERMINAL_STAMP_STATUS_VALUES,
    BreakerMetricDomain,
    InvalidDeliveryOutcomeError,
    InvalidMetricFaultFlagError,
    OutcomeMatrixFaultFlag,
)
from praetor.tickets.outbox import StampStatus


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector()


def test_disposition_distribution_increments(collector: MetricsCollector) -> None:
    collector.record_disposition(Disposition.STANDARD_REVIEW)
    collector.record_disposition(Disposition.ESCALATE)
    collector.record_disposition(Disposition.ESCALATE)
    collector.record_disposition(Disposition.AUTO_CONTAIN)

    snap = collector.snapshot()
    assert snap.disposition_counts == {
        "standard_review": 1,
        "escalate": 2,
        "auto_contain": 1,
    }


def test_policy_gate_result_alone_populates_disposition_counts(
    collector: MetricsCollector,
) -> None:
    collector.record_policy_gate_result(
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.ESCALATE,
    )

    assert collector.snapshot().disposition_counts == {"escalate": 1}


def test_policy_gate_override_rate_increments(collector: MetricsCollector) -> None:
    collector.record_policy_gate_result(
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.AUTO_CONTAIN,
    )
    collector.record_policy_gate_result(
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.ESCALATE,
    )
    collector.record_policy_gate_result(
        proposed=Disposition.STANDARD_REVIEW,
        final=Disposition.STANDARD_REVIEW,
    )

    snap = collector.snapshot()
    assert snap.policy_gate_evaluations_total == 3
    assert snap.policy_gate_override_total == 1
    assert snap.policy_gate_override_rate == pytest.approx(1 / 3)


def test_mixed_gate_and_fault_paths_do_not_double_count_dispositions(
    collector: MetricsCollector,
) -> None:
    collector.record_policy_gate_result(
        proposed=Disposition.AUTO_CONTAIN,
        final=Disposition.ESCALATE,
    )
    collector.record_policy_gate_result(
        proposed=Disposition.STANDARD_REVIEW,
        final=Disposition.STANDARD_REVIEW,
    )
    collector.record_disposition(Disposition.ESCALATE)

    snap = collector.snapshot()
    assert snap.policy_gate_evaluations_total == 2
    assert snap.disposition_counts == {
        "escalate": 2,
        "standard_review": 1,
    }


def test_llm_failure_metric_increments_per_fault_flag(
    collector: MetricsCollector,
) -> None:
    collector.record_llm_failure(OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT)
    collector.record_llm_failure(OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT)
    collector.record_llm_failure(OutcomeMatrixFaultFlag.PROVIDER_REFUSAL)

    snap = collector.snapshot()
    assert snap.llm_failure_by_fault_flag == {
        "provider_timeout": 2,
        "provider_refusal": 1,
    }


def test_llm_failure_rejects_unknown_fault_flag(
    collector: MetricsCollector,
) -> None:
    with pytest.raises(InvalidMetricFaultFlagError):
        collector.record_llm_failure("not_in_outcome_matrix")


def test_containment_directive_count_increments(
    collector: MetricsCollector,
) -> None:
    collector.record_containment_directive()
    collector.record_containment_directive()

    assert collector.snapshot().containment_directive_total == 2


def test_queue_aging_exceeded_increments(collector: MetricsCollector) -> None:
    collector.record_queue_aging_exceeded()

    assert collector.snapshot().queue_aging_exceeded_total == 1


def test_breaker_open_transitions_only_on_closed_to_open_edge(
    collector: MetricsCollector,
) -> None:
    collector.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=True,
    )
    collector.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=True,
    )
    collector.record_breaker_state(
        BreakerMetricDomain.PROVIDER_HEALTH,
        is_open=True,
    )

    snap = collector.snapshot()
    assert snap.breaker_open_transitions == {
        "containment": 1,
        "provider_health": 1,
    }
    assert snap.breaker_currently_open == {
        "containment": True,
        "provider_health": True,
    }


def test_breaker_recovery_increments_per_domain(
    collector: MetricsCollector,
) -> None:
    collector.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=True,
    )
    collector.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=False,
    )
    collector.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=True,
    )

    snap = collector.snapshot()
    assert snap.breaker_open_transitions == {"containment": 2}
    assert snap.breaker_recovery_transitions == {"containment": 1}
    assert snap.breaker_currently_open["containment"] is True


def test_provider_and_containment_breaker_state_metrics_independent(
    collector: MetricsCollector,
) -> None:
    collector.record_breaker_state(
        BreakerMetricDomain.CONTAINMENT,
        is_open=True,
    )
    collector.record_breaker_state(
        BreakerMetricDomain.PROVIDER_HEALTH,
        is_open=True,
    )
    collector.record_breaker_state(
        BreakerMetricDomain.PROVIDER_HEALTH,
        is_open=False,
    )

    snap = collector.snapshot()
    assert snap.breaker_open_transitions == {
        "containment": 1,
        "provider_health": 1,
    }
    assert snap.breaker_recovery_transitions == {"provider_health": 1}
    assert snap.breaker_currently_open == {
        "containment": True,
        "provider_health": False,
    }


def test_probe_outcome_metrics_independent_from_production_call_metrics(
    collector: MetricsCollector,
) -> None:
    collector.record_production_call_outcome(success=False)
    collector.record_production_call_outcome(success=False)
    collector.record_probe_outcome(success=True)

    snap = collector.snapshot()
    assert snap.production_failure_total == 2
    assert snap.production_success_total == 0
    assert snap.probe_success_total == 1
    assert snap.probe_failure_total == 0


def test_probe_rate_limit_metric_tracks_probe_rate_limit_per_minute(
    collector: MetricsCollector,
) -> None:
    collector.record_probe_rate_limited(limit_per_minute=5)
    collector.record_probe_rate_limited(limit_per_minute=5)

    snap = collector.snapshot()
    assert snap.probe_rate_limited_total == 2
    assert snap.probe_rate_limit_per_minute == 5


def test_configure_probe_rate_limit_without_throttling_event(
    collector: MetricsCollector,
) -> None:
    collector.configure_probe_rate_limit(limit_per_minute=12)

    snap = collector.snapshot()
    assert snap.probe_rate_limit_per_minute == 12
    assert snap.probe_rate_limited_total == 0


def test_stamp_status_metric_increments(collector: MetricsCollector) -> None:
    collector.record_stamp_status(StampStatus.SUCCEEDED)
    collector.record_stamp_status(StampStatus.FAILED)
    collector.record_stamp_status(StampStatus.UNKNOWN)
    collector.record_stamp_status(StampStatus.PENDING)

    snap = collector.snapshot()
    assert snap.stamp_status_counts == {
        "succeeded": 1,
        "failed": 1,
        "unknown": 1,
        "pending": 1,
    }


def test_stamp_status_terminal_and_non_terminal_views(
    collector: MetricsCollector,
) -> None:
    collector.record_stamp_status(StampStatus.PENDING)
    collector.record_stamp_status(StampStatus.SUCCEEDED)
    collector.record_stamp_status(StampStatus.FAILED)

    snap = collector.snapshot()
    assert snap.stamp_status_non_terminal_counts == {"pending": 1}
    assert snap.stamp_status_terminal_counts == {
        "succeeded": 1,
        "failed": 1,
    }


def test_health_alert_delivery_status_metric_increments_per_channel(
    collector: MetricsCollector,
) -> None:
    collector.record_health_alert_delivery("jsonl", DeliveryStatus.SUCCEEDED)
    collector.record_health_alert_delivery("jsonl", DeliveryStatus.FAILED)
    collector.record_health_alert_delivery("stdout", DeliveryStatus.SUCCEEDED)

    snap = collector.snapshot()
    assert snap.health_alert_delivery_by_channel == {
        "jsonl": {"succeeded": 1, "failed": 1},
        "stdout": {"succeeded": 1},
    }


def test_health_alert_delivery_rejects_pending_outcome(
    collector: MetricsCollector,
) -> None:
    with pytest.raises(InvalidDeliveryOutcomeError):
        collector.record_health_alert_delivery("jsonl", DeliveryStatus.PENDING)


def test_feed_export_lag_recorded_per_record(collector: MetricsCollector) -> None:
    commit_at = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    threshold = 60.0

    collector.record_feed_export_lag(
        ledger_commit_at=commit_at,
        export_completed_at=commit_at + timedelta(seconds=10),
        warning_threshold_seconds=threshold,
    )
    collector.record_feed_export_lag(
        ledger_commit_at=commit_at,
        export_completed_at=commit_at + timedelta(seconds=30),
        warning_threshold_seconds=threshold,
    )

    snap = collector.snapshot()
    assert snap.feed_export_lag_samples == (10.0, 30.0)


def test_feed_export_lag_window_caps_samples() -> None:
    window = 5
    collector = MetricsCollector(feed_lag_sample_window=window)
    base = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    for lag in range(1, window + 6):
        collector.record_feed_export_lag(
            ledger_commit_at=base,
            export_completed_at=base + timedelta(seconds=lag),
            warning_threshold_seconds=60.0,
        )

    snap = collector.snapshot()
    assert len(snap.feed_export_lag_samples) == window
    assert snap.feed_export_lag_samples == (6.0, 7.0, 8.0, 9.0, 10.0)


def test_p99_feed_export_lag_and_warning_threshold_metric_exist(
    collector: MetricsCollector,
) -> None:
    threshold = 50.0
    base = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    for lag in range(1, 101):
        collector.record_feed_export_lag(
            ledger_commit_at=base,
            export_completed_at=base + timedelta(seconds=lag),
            warning_threshold_seconds=threshold,
        )

    snap = collector.snapshot()
    assert snap.feed_export_lag_warning_threshold_seconds == threshold
    assert snap.feed_export_lag_p99_seconds == compute_p99(list(range(1, 101)))
    assert snap.feed_export_lag_p99_seconds == 99.0
    assert snap.feed_export_lag_warning_exceeded is True


def test_feed_export_lag_clamps_negative_and_zero_lag(
    collector: MetricsCollector,
) -> None:
    commit_at = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)

    collector.record_feed_export_lag(
        ledger_commit_at=commit_at,
        export_completed_at=commit_at,
        warning_threshold_seconds=10.0,
    )
    collector.record_feed_export_lag(
        ledger_commit_at=commit_at,
        export_completed_at=commit_at - timedelta(seconds=5),
        warning_threshold_seconds=10.0,
    )

    assert collector.snapshot().feed_export_lag_samples == (0.0, 0.0)


def test_compute_p99_for_small_sample_sizes() -> None:
    assert compute_p99([7.0]) == 7.0
    assert compute_p99([3.0, 9.0]) == 3.0


def test_feed_export_lag_warning_at_threshold_boundary(
    collector: MetricsCollector,
) -> None:
    commit_at = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    collector.record_feed_export_lag(
        ledger_commit_at=commit_at,
        export_completed_at=commit_at + timedelta(seconds=10),
        warning_threshold_seconds=10.0,
    )

    snap = collector.snapshot()
    assert snap.feed_export_lag_p99_seconds == 10.0
    assert snap.feed_export_lag_warning_exceeded is True


def test_revocation_feed_unhealthy_transition_metric_increments(
    collector: MetricsCollector,
) -> None:
    collector.record_revocation_feed_unhealthy_transition()
    collector.record_revocation_feed_unhealthy_transition()

    assert collector.snapshot().revocation_feed_unhealthy_transitions == 2


def test_snapshot_keys_use_canonical_enum_values(
    collector: MetricsCollector,
) -> None:
    for status in StampStatus:
        collector.record_stamp_status(status)
    collector.record_llm_failure(OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT)
    for channel in V1_DELIVERY_CHANNELS:
        collector.record_health_alert_delivery(channel, DeliveryStatus.SUCCEEDED)

    snap = collector.snapshot()
    assert set(snap.stamp_status_counts) == {status.value for status in StampStatus}
    assert set(snap.llm_failure_by_fault_flag) == {"provider_timeout"}
    assert set(snap.health_alert_delivery_by_channel) == set(V1_DELIVERY_CHANNELS)
    assert set(snap.stamp_status_terminal_counts) <= TERMINAL_STAMP_STATUS_VALUES


def test_default_feed_lag_window_matches_constant() -> None:
    collector = MetricsCollector()
    base = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
    for lag in range(1, DEFAULT_FEED_LAG_SAMPLE_WINDOW + 50):
        collector.record_feed_export_lag(
            ledger_commit_at=base,
            export_completed_at=base + timedelta(seconds=lag),
            warning_threshold_seconds=60.0,
        )

    assert len(collector.snapshot().feed_export_lag_samples) == (
        DEFAULT_FEED_LAG_SAMPLE_WINDOW
    )


def test_record_correlation_unsupported_event_id_increments_snapshot() -> None:
    from praetor.metrics.collector import MetricsCollector

    collector = MetricsCollector()
    collector.record_correlation_unsupported_event_id()
    collector.record_correlation_unsupported_event_id()

    snap = collector.snapshot()
    assert snap.correlation_unsupported_event_id_total == 2
