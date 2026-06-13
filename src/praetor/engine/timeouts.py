"""Provider judgment latency SLA tracking for intake."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.provider import (
    JudgmentProvider,
    JudgmentRequest,
    ProviderRetryPolicy,
    call_provider_with_retries,
)

# v1 provisional until org-config contract pins max_provider_judgment_latency_seconds.
V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS = 30


def provider_latency_sla_exceeded(
    elapsed_seconds: float,
    *,
    max_latency_seconds: int = V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS,
) -> bool:
    """Return True when elapsed wall time exceeds the configured judgment SLA."""
    return elapsed_seconds > max_latency_seconds


@dataclass(frozen=True)
class TrackedProviderCall:
    judgment: ModelJudgment
    elapsed_seconds: float
    sla_exceeded: bool


def call_provider_with_latency_tracking(
    provider: JudgmentProvider,
    request: JudgmentRequest,
    *,
    retry_policy: ProviderRetryPolicy | None = None,
    max_latency_seconds: int = V1_DEFAULT_MAX_PROVIDER_JUDGMENT_LATENCY_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> TrackedProviderCall:
    """Time the full retry loop (attempts plus backoff) for end-to-end SLA (DEC-039)."""
    started = monotonic()
    judgment = call_provider_with_retries(
        provider,
        request,
        retry_policy=retry_policy,
        sleep=sleep,
    )
    elapsed = monotonic() - started
    return TrackedProviderCall(
        judgment=judgment,
        elapsed_seconds=elapsed,
        sla_exceeded=provider_latency_sla_exceeded(
            elapsed,
            max_latency_seconds=max_latency_seconds,
        ),
    )
