"""SystemHealthAlert outbox and v1 delivery (docs/plan.md Task 8)."""

from praetor.alerts.outbox import (
    V1_DELIVERY_CHANNELS,
    DeliveryAttempt,
    DeliveryStatus,
    DuplicateHealthAlertError,
    HealthAlertOutboxEntry,
    ensure_health_alert_outbox_schema,
    fetch_delivery_attempt,
    fetch_health_alert_outbox,
    fetch_retryable_delivery_attempts,
    init_health_alert_outbox_schema,
    record_delivery_attempt,
    write_pending_health_alert,
)
from praetor.alerts.system_health import (
    HealthAlertSink,
    JsonlSink,
    StdoutSink,
    deliver_health_alerts,
    emit_system_health_alert,
)

__all__ = [
    "DeliveryAttempt",
    "DeliveryStatus",
    "DuplicateHealthAlertError",
    "HealthAlertOutboxEntry",
    "HealthAlertSink",
    "JsonlSink",
    "StdoutSink",
    "V1_DELIVERY_CHANNELS",
    "deliver_health_alerts",
    "emit_system_health_alert",
    "ensure_health_alert_outbox_schema",
    "fetch_delivery_attempt",
    "fetch_health_alert_outbox",
    "fetch_retryable_delivery_attempts",
    "init_health_alert_outbox_schema",
    "record_delivery_attempt",
    "write_pending_health_alert",
]
