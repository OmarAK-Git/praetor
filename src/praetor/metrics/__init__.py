"""In-process operational metrics collector."""

from praetor.metrics.collector import MetricsCollector, compute_p99
from praetor.metrics.events import (
    DEFAULT_FEED_LAG_SAMPLE_WINDOW,
    LLM_FAILURE_FAULT_FLAGS,
    BreakerMetricDomain,
    InvalidDeliveryChannelError,
    InvalidDeliveryOutcomeError,
    InvalidMetricFaultFlagError,
    MetricsSnapshot,
    OutcomeMatrixFaultFlag,
)

__all__ = [
    "DEFAULT_FEED_LAG_SAMPLE_WINDOW",
    "BreakerMetricDomain",
    "InvalidDeliveryChannelError",
    "InvalidDeliveryOutcomeError",
    "InvalidMetricFaultFlagError",
    "LLM_FAILURE_FAULT_FLAGS",
    "MetricsCollector",
    "MetricsSnapshot",
    "OutcomeMatrixFaultFlag",
    "compute_p99",
]
