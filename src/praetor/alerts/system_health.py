"""SystemHealthAlert emit and v1 delivery (JSONL + stdout).

JSONL delivery is at-least-once: if a write succeeds and the process crashes
before ``record_delivery_attempt``, retry appends a duplicate line for the same
``alert_id``. Consumers must dedupe on ``alert_id`` (or equivalent payload
identity); v1 does not provide exactly-once file output.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

from praetor.alerts.outbox import (
    V1_DELIVERY_CHANNELS,
    DeliveryStatus,
    HealthAlertOutboxEntry,
    fetch_retryable_delivery_attempts,
    record_delivery_attempt,
    write_pending_health_alert,
)
from praetor.contracts.health import SystemHealthAlert


class HealthAlertSink(Protocol):
    """Delivery sink for a single channel.

    Sink failures (any ``Exception``) are recorded as channel ``failed`` and
    remain retryable; sinks must not swallow errors silently.
    """

    channel: str

    def write_line(self, line: str) -> None:
        """Deliver one canonical JSON line."""


@dataclass
class JsonlSink:
    """Append canonical JSON lines to a JSONL file."""

    path: Path
    channel: str = "jsonl"

    def write_line(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


@dataclass
class StdoutSink:
    """Write canonical JSON lines to stdout or an injected stream."""

    stream: TextIO | None = None
    channel: str = "stdout"

    def write_line(self, line: str) -> None:
        import sys

        target = self.stream if self.stream is not None else sys.stdout
        target.write(line + "\n")
        target.flush()


def _deliver_to_sink(
    conn: sqlite3.Connection,
    alert_id: str,
    line: str,
    sink: HealthAlertSink,
) -> None:
    try:
        sink.write_line(line)
    except Exception as exc:
        record_delivery_attempt(
            conn,
            alert_id,
            sink.channel,
            DeliveryStatus.FAILED,
            {
                "error": str(exc),
                "exception_type": type(exc).__name__,
                "channel": sink.channel,
            },
        )
        return
    record_delivery_attempt(
        conn,
        alert_id,
        sink.channel,
        DeliveryStatus.SUCCEEDED,
        {"channel": sink.channel},
    )


def deliver_health_alerts(
    conn: sqlite3.Connection,
    *,
    jsonl_sink: HealthAlertSink,
    stdout_sink: HealthAlertSink,
) -> int:
    """Retry pending/failed v1 channel deliveries. Returns attempts processed."""
    sinks = {jsonl_sink.channel: jsonl_sink, stdout_sink.channel: stdout_sink}
    retryable = fetch_retryable_delivery_attempts(conn)
    processed = 0
    for entry, attempt in retryable:
        if attempt.channel not in V1_DELIVERY_CHANNELS:
            continue
        sink = sinks.get(attempt.channel)
        if sink is None:
            continue
        line = entry.alert.model_dump_json()
        _deliver_to_sink(conn, entry.alert_id, line, sink)
        processed += 1
    return processed


def emit_system_health_alert(
    conn: sqlite3.Connection,
    alert: SystemHealthAlert,
    *,
    jsonl_sink: HealthAlertSink,
    stdout_sink: HealthAlertSink,
    deliver: bool = True,
    alert_id: str | None = None,
) -> HealthAlertOutboxEntry:
    """Persist alert (and pending delivery rows) then optionally deliver."""
    entry = write_pending_health_alert(conn, alert, alert_id=alert_id)
    if deliver:
        deliver_health_alerts(
            conn,
            jsonl_sink=jsonl_sink,
            stdout_sink=stdout_sink,
        )
    return entry
