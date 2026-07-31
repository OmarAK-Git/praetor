"""Metric event kinds, canonical keys, and exported snapshot models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from praetor.alerts.outbox import V1_DELIVERY_CHANNELS, DeliveryStatus
from praetor.tickets.outbox import TERMINAL_STAMP_STATUSES, StampStatus

DEFAULT_FEED_LAG_SAMPLE_WINDOW = 1000

TERMINAL_STAMP_STATUS_VALUES = frozenset(
    status.value for status in TERMINAL_STAMP_STATUSES
)
NON_TERMINAL_STAMP_STATUS_VALUES = frozenset(
    status.value
    for status in StampStatus
    if status.value not in TERMINAL_STAMP_STATUS_VALUES
)

DELIVERY_OUTCOME_STATUSES = frozenset(
    {DeliveryStatus.SUCCEEDED, DeliveryStatus.FAILED}
)


class BreakerMetricDomain(StrEnum):
    """Independent breaker domains tracked by metrics."""

    CONTAINMENT = "containment"
    PROVIDER_HEALTH = "provider_health"


class OutcomeMatrixFaultFlag(StrEnum):
    """Fault flags from ``docs/contracts.md`` §13."""

    CORRELATION_FAILURE = "correlation_failure"
    CONFIG_OVER_BUDGET = "config_over_budget"
    INVALID_MODEL_CITATION = "invalid_model_citation"
    PROVIDER_MALFORMED_JSON = "provider_malformed_json"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_REFUSAL = "provider_refusal"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    AGENTIC_EVIDENCE_GATHERING_FAILED = "agentic_evidence_gathering_failed"
    NEVER_CONTAIN_SNAPSHOT = "never_contain_snapshot"
    NEVER_CONTAIN_LIVE_CONFLICT = "never_contain_live_conflict"
    AMBIGUOUS_TARGET_IDENTITY = "ambiguous_target_identity"
    AMBIGUOUS_CONTAINMENT_TARGET = "ambiguous_containment_target"
    INSUFFICIENT_CORROBORATION = "insufficient_corroboration"
    ACCOUNT_CONTAINMENT_DISABLED = "account_containment_disabled"
    POLICY_AMBIGUITY = "policy_ambiguity"
    CONTAINMENT_POLICY_DENIED = "containment_policy_denied"
    CONTAINMENT_POLICY_ESCALATION_REQUIRED = "containment_policy_escalation_required"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CONTAINMENT_BREAKER_OPEN = "containment_breaker_open"
    PROVIDER_HEALTH_BREAKER_OPEN = "provider_health_breaker_open"
    REVOCATION_FEED_UNHEALTHY = "revocation_feed_unhealthy"
    LATENCY_SLA_EXCEEDED = "latency_sla_exceeded"
    QUEUE_AGING_EXCEEDED = "queue_aging_exceeded"
    TICKET_STAMP_FAILED = "ticket_stamp_failed"
    LEDGER_CHAIN_INTEGRITY_FAILURE = "ledger_chain_integrity_failure"


LLM_FAILURE_FAULT_FLAGS = frozenset(
    {
        OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION,
        OutcomeMatrixFaultFlag.PROVIDER_MALFORMED_JSON,
        OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT,
        OutcomeMatrixFaultFlag.PROVIDER_REFUSAL,
        OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE,
    }
)


def is_llm_failure_fault_flag(
    fault_flag: OutcomeMatrixFaultFlag | str,
) -> bool:
    """Return whether ``fault_flag`` is an approved LLM/provider failure metric."""
    return normalize_fault_flag(fault_flag) in LLM_FAILURE_FAULT_FLAGS


class InvalidMetricFaultFlagError(ValueError):
    """Raised when a fault flag is not in the Outcome Matrix set."""


class InvalidDeliveryChannelError(ValueError):
    """Raised when a health-alert delivery channel is not in v1 channels."""


class InvalidDeliveryOutcomeError(ValueError):
    """Raised when metrics record a non-terminal delivery status."""


def validate_delivery_channel(channel: str) -> str:
    if channel not in V1_DELIVERY_CHANNELS:
        allowed = sorted(V1_DELIVERY_CHANNELS)
        msg = f"unknown delivery channel {channel!r}; expected one of {allowed}"
        raise InvalidDeliveryChannelError(msg)
    return channel


def validate_delivery_outcome(status: DeliveryStatus) -> DeliveryStatus:
    if status not in DELIVERY_OUTCOME_STATUSES:
        msg = "metrics record terminal delivery outcomes only (succeeded or failed)"
        raise InvalidDeliveryOutcomeError(msg)
    return status


def normalize_fault_flag(
    fault_flag: OutcomeMatrixFaultFlag | str,
) -> OutcomeMatrixFaultFlag:
    if isinstance(fault_flag, OutcomeMatrixFaultFlag):
        return fault_flag
    try:
        return OutcomeMatrixFaultFlag(fault_flag)
    except ValueError as exc:
        msg = f"unknown Outcome Matrix fault flag {fault_flag!r}"
        raise InvalidMetricFaultFlagError(msg) from exc


@dataclass(frozen=True)
class MetricsSnapshot:
    """Point-in-time view of all Task 24 metrics."""

    disposition_counts: dict[str, int]
    policy_gate_evaluations_total: int
    policy_gate_override_total: int
    llm_failure_by_fault_flag: dict[str, int]
    containment_directive_total: int
    queue_aging_exceeded_total: int
    breaker_open_transitions: dict[str, int]
    breaker_recovery_transitions: dict[str, int]
    breaker_currently_open: dict[str, bool]
    probe_success_total: int
    probe_failure_total: int
    production_success_total: int
    production_failure_total: int
    probe_rate_limited_total: int
    probe_rate_limit_per_minute: int | None
    stamp_status_counts: dict[str, int]
    health_alert_delivery_by_channel: dict[str, dict[str, int]]
    feed_export_lag_samples: tuple[float, ...]
    feed_export_lag_p99_seconds: float | None
    feed_export_lag_warning_threshold_seconds: float | None
    feed_export_lag_warning_exceeded: bool
    revocation_feed_unhealthy_transitions: int
    correlation_unsupported_event_id_total: int

    @property
    def policy_gate_override_rate(self) -> float:
        if self.policy_gate_evaluations_total == 0:
            return 0.0
        return self.policy_gate_override_total / self.policy_gate_evaluations_total

    @property
    def stamp_status_terminal_counts(self) -> dict[str, int]:
        return {
            key: count
            for key, count in self.stamp_status_counts.items()
            if key in TERMINAL_STAMP_STATUS_VALUES
        }

    @property
    def stamp_status_non_terminal_counts(self) -> dict[str, int]:
        return {
            key: count
            for key, count in self.stamp_status_counts.items()
            if key in NON_TERMINAL_STAMP_STATUS_VALUES
        }
