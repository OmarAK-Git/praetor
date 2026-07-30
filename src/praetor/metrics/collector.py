"""In-process metrics collector for Task 24 observability counters."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

from praetor.alerts.outbox import DeliveryStatus
from praetor.contracts.disposition import Disposition
from praetor.metrics.events import (
    DEFAULT_FEED_LAG_SAMPLE_WINDOW,
    BreakerMetricDomain,
    MetricsSnapshot,
    OutcomeMatrixFaultFlag,
    normalize_fault_flag,
    validate_delivery_channel,
    validate_delivery_outcome,
)
from praetor.tickets.outbox import StampStatus


def compute_p99(samples: list[float]) -> float | None:
    """Return the 99th percentile lag in seconds, or None when empty."""
    if not samples:
        return None
    ordered = sorted(samples)
    index = max(0, int(0.99 * len(ordered)) - 1)
    return ordered[index]


class MetricsCollector:
    """Thread-unsafe in-process collector; v1 single-writer process assumption.

    ``record_policy_gate_result`` records the final disposition internally.
    Callers that route through PolicyGate must **not** also call
    ``record_disposition`` for the same alert. Use ``record_disposition`` only
    for paths that bypass PolicyGate (for example correlation or config faults).
    """

    def __init__(
        self,
        *,
        feed_lag_sample_window: int = DEFAULT_FEED_LAG_SAMPLE_WINDOW,
    ) -> None:
        if feed_lag_sample_window < 1:
            msg = "feed_lag_sample_window must be at least 1"
            raise ValueError(msg)
        self._feed_lag_sample_window = feed_lag_sample_window
        self._disposition_counts: dict[str, int] = defaultdict(int)
        self._policy_gate_evaluations_total = 0
        self._policy_gate_override_total = 0
        self._llm_failure_by_fault_flag: dict[str, int] = defaultdict(int)
        self._containment_directive_total = 0
        self._queue_aging_exceeded_total = 0
        self._breaker_open_transitions: dict[str, int] = defaultdict(int)
        self._breaker_recovery_transitions: dict[str, int] = defaultdict(int)
        self._breaker_currently_open: dict[str, bool] = defaultdict(bool)
        self._probe_success_total = 0
        self._probe_failure_total = 0
        self._production_success_total = 0
        self._production_failure_total = 0
        self._probe_rate_limited_total = 0
        self._probe_rate_limit_per_minute: int | None = None
        self._stamp_status_counts: dict[str, int] = defaultdict(int)
        self._health_alert_delivery_by_channel: dict[str, dict[str, int]] = (
            defaultdict(lambda: defaultdict(int))
        )
        self._feed_export_lag_samples: deque[float] = deque(
            maxlen=feed_lag_sample_window
        )
        self._feed_export_lag_warning_threshold_seconds: float | None = None
        self._revocation_feed_unhealthy_transitions = 0
        self._correlation_unsupported_event_id_total = 0

    def record_disposition(self, disposition: Disposition | str) -> None:
        key = disposition.value if isinstance(disposition, Disposition) else disposition
        self._disposition_counts[key] += 1

    def record_policy_gate_result(
        self,
        *,
        proposed: Disposition | str,
        final: Disposition | str,
    ) -> None:
        proposed_key = proposed.value if isinstance(proposed, Disposition) else proposed
        final_key = final.value if isinstance(final, Disposition) else final
        self._policy_gate_evaluations_total += 1
        if proposed_key != final_key:
            self._policy_gate_override_total += 1
        self.record_disposition(final_key)

    def record_llm_failure(
        self,
        fault_flag: OutcomeMatrixFaultFlag | str,
    ) -> None:
        """Increment LLM/provider failure counters for a §13 fault flag.

        Validation accepts the full Outcome Matrix set; production wiring should
        pass only provider/model-quality flags (see ``LLM_FAILURE_FAULT_FLAGS``).
        """
        normalized = normalize_fault_flag(fault_flag)
        self._llm_failure_by_fault_flag[normalized.value] += 1

    def record_containment_directive(self) -> None:
        self._containment_directive_total += 1

    def record_queue_aging_exceeded(self) -> None:
        """Record an Outcome Matrix ``queue_aging_exceeded`` escalation."""
        self._queue_aging_exceeded_total += 1

    def record_breaker_state(
        self,
        domain: BreakerMetricDomain,
        *,
        is_open: bool,
    ) -> None:
        domain_key = domain.value
        previously_open = self._breaker_currently_open[domain_key]
        if is_open:
            if not previously_open:
                self._breaker_open_transitions[domain_key] += 1
            self._breaker_currently_open[domain_key] = True
            return
        if previously_open:
            self._breaker_recovery_transitions[domain_key] += 1
        self._breaker_currently_open[domain_key] = False

    def record_probe_outcome(self, *, success: bool) -> None:
        if success:
            self._probe_success_total += 1
        else:
            self._probe_failure_total += 1

    def record_production_call_outcome(self, *, success: bool) -> None:
        if success:
            self._production_success_total += 1
        else:
            self._production_failure_total += 1

    def configure_probe_rate_limit(self, *, limit_per_minute: int) -> None:
        """Record the configured probe rate limit without a throttling event."""
        self._probe_rate_limit_per_minute = limit_per_minute

    def record_probe_rate_limited(self, *, limit_per_minute: int) -> None:
        self.configure_probe_rate_limit(limit_per_minute=limit_per_minute)
        self._probe_rate_limited_total += 1

    def record_stamp_status(self, status: StampStatus) -> None:
        self._stamp_status_counts[status.value] += 1

    def record_health_alert_delivery(
        self,
        channel: str,
        status: DeliveryStatus,
    ) -> None:
        channel_key = validate_delivery_channel(channel)
        outcome = validate_delivery_outcome(status)
        self._health_alert_delivery_by_channel[channel_key][outcome.value] += 1

    def record_feed_export_lag(
        self,
        *,
        ledger_commit_at: datetime,
        export_completed_at: datetime,
        warning_threshold_seconds: float,
    ) -> None:
        lag = (export_completed_at - ledger_commit_at).total_seconds()
        if lag < 0:
            lag = 0.0
        self._feed_export_lag_samples.append(lag)
        self._feed_export_lag_warning_threshold_seconds = warning_threshold_seconds

    def record_revocation_feed_unhealthy_transition(self) -> None:
        self._revocation_feed_unhealthy_transitions += 1

    def record_correlation_unsupported_event_id(self) -> None:
        """Record a telemetry event skipped because its EventID is unsupported.

        Distinguishes a schema-mismatch cause of an empty/short EvidenceBundle
        from genuinely empty telemetry, since both currently downgrade to the
        same ``correlation_failure`` disposition path.
        """
        self._correlation_unsupported_event_id_total += 1

    def snapshot(self) -> MetricsSnapshot:
        lag_samples = list(self._feed_export_lag_samples)
        p99 = compute_p99(lag_samples)
        threshold = self._feed_export_lag_warning_threshold_seconds
        warning_exceeded = (
            p99 is not None
            and threshold is not None
            and p99 >= threshold
        )
        return MetricsSnapshot(
            disposition_counts=dict(self._disposition_counts),
            policy_gate_evaluations_total=self._policy_gate_evaluations_total,
            policy_gate_override_total=self._policy_gate_override_total,
            llm_failure_by_fault_flag=dict(self._llm_failure_by_fault_flag),
            containment_directive_total=self._containment_directive_total,
            queue_aging_exceeded_total=self._queue_aging_exceeded_total,
            breaker_open_transitions=dict(self._breaker_open_transitions),
            breaker_recovery_transitions=dict(self._breaker_recovery_transitions),
            breaker_currently_open=dict(self._breaker_currently_open),
            probe_success_total=self._probe_success_total,
            probe_failure_total=self._probe_failure_total,
            production_success_total=self._production_success_total,
            production_failure_total=self._production_failure_total,
            probe_rate_limited_total=self._probe_rate_limited_total,
            probe_rate_limit_per_minute=self._probe_rate_limit_per_minute,
            stamp_status_counts=dict(self._stamp_status_counts),
            health_alert_delivery_by_channel={
                channel: dict(status_counts)
                for channel, status_counts in (
                    self._health_alert_delivery_by_channel.items()
                )
            },
            feed_export_lag_samples=tuple(lag_samples),
            feed_export_lag_p99_seconds=p99,
            feed_export_lag_warning_threshold_seconds=threshold,
            feed_export_lag_warning_exceeded=warning_exceeded,
            revocation_feed_unhealthy_transitions=(
                self._revocation_feed_unhealthy_transitions
            ),
            correlation_unsupported_event_id_total=(
                self._correlation_unsupported_event_id_total
            ),
        )
