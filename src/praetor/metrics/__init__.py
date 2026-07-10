"""In-process operational metrics collector."""

from praetor.metrics.collector import MetricsCollector, compute_p99
from praetor.metrics.evaluations import (
    PolicyGateEvaluationRow,
    init_policy_gate_evaluation_schema,
    record_policy_gate_evaluation,
)
from praetor.metrics.events import (
    DEFAULT_FEED_LAG_SAMPLE_WINDOW,
    LLM_FAILURE_FAULT_FLAGS,
    BreakerMetricDomain,
    InvalidDeliveryChannelError,
    InvalidDeliveryOutcomeError,
    InvalidMetricFaultFlagError,
    MetricsSnapshot,
    OutcomeMatrixFaultFlag,
    is_llm_failure_fault_flag,
)

__all__ = [
    "PolicyGateEvaluationRow",
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
    "init_policy_gate_evaluation_schema",
    "is_llm_failure_fault_flag",
    "record_policy_gate_evaluation",
]
