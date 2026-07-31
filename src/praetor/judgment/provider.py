"""Provider Protocol and bounded retry helpers for model judgment calls."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from pydantic import ValidationError

from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.judgment import ModelJudgment


class ProviderError(Exception):
    """Base class for provider failures that map to Outcome Matrix rows."""


class ProviderTimeoutError(ProviderError):
    """Provider did not return before the bounded timeout/retry window closed."""


class ProviderMalformedResponseError(ProviderError):
    """Provider output was not valid JSON for the ModelJudgment contract."""


class ProviderRefusalError(ProviderError):
    """Provider refused to produce a judgment for the supplied request."""


class ProviderUnavailableError(ProviderError):
    """Provider integration exists but is not configured for live calls."""


PROVIDER_HEALTH_CANARY_PAYLOAD: Mapping[str, str] = MappingProxyType(
    {"canary": "praetor-provider-health-probe-v1"}
)


@dataclass(frozen=True)
class JudgmentRequest:
    """Minimal Task 13 request shape; Task 14 owns prompt/excerpt contents."""

    scenario_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    evidence_bundle: EvidenceBundle | None = None
    """Resolved EvidenceBundle for this intake when available. Unused by
    single-shot providers; agentic-mode providers require it for tools."""


@dataclass(frozen=True)
class ProviderProbeResult:
    success: bool
    provider_name: str
    model_name: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderRetryPolicy:
    max_attempts: int = 2
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            msg = "max_attempts must be at least 1"
            raise ValueError(msg)
        if self.backoff_seconds < 0:
            msg = "backoff_seconds must be non-negative"
            raise ValueError(msg)


@runtime_checkable
class JudgmentProvider(Protocol):
    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        """Return a structured model judgment or raise a typed provider failure."""

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        """Run a synthetic provider-health probe with no production alert data."""


def parse_model_judgment_json(raw_json: str) -> ModelJudgment:
    try:
        data = json.loads(raw_json)
        return ModelJudgment.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        msg = "provider returned malformed ModelJudgment JSON"
        raise ProviderMalformedResponseError(msg) from exc


def call_provider_with_retries(
    provider: JudgmentProvider,
    request: JudgmentRequest,
    *,
    retry_policy: ProviderRetryPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ModelJudgment:
    policy = retry_policy or ProviderRetryPolicy()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return provider.generate_judgment(request)
        except ProviderTimeoutError:
            if attempt == policy.max_attempts:
                raise
            if policy.backoff_seconds > 0:
                sleep(policy.backoff_seconds)
    raise AssertionError("unreachable provider retry loop")
