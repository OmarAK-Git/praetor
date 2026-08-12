"""Spike-local Vertex/Gemini provider (evals only — not production).

Fixes generationConfig underspecification discovered by the Path B smoke:
``responseMimeType`` alone enables JSON mode without a schema, max output,
or thinking budget. On gemini-2.5-flash that lets reasoning tokens consume
the output budget and surface truncated JSON as a parse error.

Also treats non-refusal terminal finishReasons (``MAX_TOKENS`` et al.) as
explicit failures instead of falling through to ``parse_model_judgment_json``.

Must not land in ``src/praetor/`` — design forbids src/ changes for the spike.
A separate production ticket should land the finishReason distinction in
``vertex_provider.py``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderProbeResult,
    ProviderRefusalError,
    ProviderUnavailableError,
    parse_model_judgment_json,
)
from praetor.judgment.vertex_provider import (
    REFUSAL_FINISH_REASONS,
    judgment_prompt_from_request,
)

DEFAULT_SPIKE_MODEL = "gemini-2.5-flash"
DEFAULT_LOCATION = "us-central1"
DEFAULT_MAX_OUTPUT_TOKENS = 16384
DEFAULT_THINKING_BUDGET = 0
# Non-zero: three runs per (anchor, path) measure variance; T=0 makes that vacuous.
DEFAULT_TEMPERATURE = 1.0

# Non-refusal terminals that still mean the run failed (output not complete).
TERMINAL_OUTPUT_FAILURE_REASONS = frozenset(
    {
        "MAX_TOKENS",
        "FinishReason.MAX_TOKENS",
        "LENGTH",
        "FinishReason.LENGTH",
    }
)


class ProviderOutputTruncatedError(ProviderError):
    """Provider stopped for length / max tokens — not a schema parse failure."""


def _normalize_finish_reason(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw)
    # Enum-like "FinishReason.MAX_TOKENS" → "MAX_TOKENS"
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.upper()


def _project_id() -> str:
    for key in ("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "PRAETOR_GCP_PROJECT"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    msg = "set GOOGLE_CLOUD_PROJECT for spike Vertex provider"
    raise ProviderUnavailableError(msg)


@dataclass(frozen=True)
class SpikeVertexProvider:
    """JudgmentProvider using Vertex ADC with constrained generationConfig."""

    model_name: str = DEFAULT_SPIKE_MODEL
    provider_name: str = "vertex-spike"
    project: str | None = None
    location: str = DEFAULT_LOCATION
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    thinking_budget: int = DEFAULT_THINKING_BUDGET
    temperature: float = DEFAULT_TEMPERATURE
    timeout_seconds: float = 300.0

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        result = self.generate_judgment_detailed(request)
        return result["judgment"]

    def generate_judgment_detailed(
        self, request: JudgmentRequest
    ) -> dict[str, Any]:
        """Like ``generate_judgment`` but also returns finishReason / usage."""
        prompt = judgment_prompt_from_request(request)
        project = self.project or _project_id()
        client = genai.Client(
            vertexai=True, project=project, location=self.location
        )
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ModelJudgment,
            max_output_tokens=self.max_output_tokens,
            temperature=self.temperature,
            thinking_config=types.ThinkingConfig(
                thinking_budget=self.thinking_budget
            ),
            http_options=types.HttpOptions(
                timeout=int(self.timeout_seconds * 1000)
            ),
        )
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 — map SDK errors to provider faults
            msg = f"spike vertex call failed: {exc}"
            raise ProviderUnavailableError(msg) from exc

        finish_reason = None
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            finish_reason = _normalize_finish_reason(
                getattr(candidates[0], "finish_reason", None)
            )

        usage: dict[str, Any] = {}
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            usage = {
                "promptTokenCount": getattr(meta, "prompt_token_count", None),
                "candidatesTokenCount": getattr(
                    meta, "candidates_token_count", None
                ),
                "totalTokenCount": getattr(meta, "total_token_count", None),
                "thoughtsTokenCount": getattr(
                    meta, "thoughts_token_count", None
                ),
            }

        if finish_reason and finish_reason in {
            _normalize_finish_reason(r) for r in REFUSAL_FINISH_REASONS
        }:
            msg = f"spike vertex refused judgment: finishReason={finish_reason}"
            raise ProviderRefusalError(msg)

        if finish_reason and any(
            finish_reason == _normalize_finish_reason(r)
            or finish_reason.endswith(r)
            for r in ("MAX_TOKENS", "LENGTH")
        ):
            msg = (
                f"spike vertex output truncated: finishReason={finish_reason}"
            )
            raise ProviderOutputTruncatedError(msg)

        raw_text = (getattr(response, "text", None) or "").strip()
        if not raw_text:
            msg = (
                "spike vertex response missing candidate text"
                + (f" (finishReason={finish_reason})" if finish_reason else "")
            )
            raise ProviderMalformedResponseError(msg)

        try:
            judgment = parse_model_judgment_json(raw_text)
        except ProviderMalformedResponseError:
            # Preserve finishReason in the message so probes never invent a
            # schema failure when the cause was length.
            msg = (
                "provider returned malformed ModelJudgment JSON"
                + (f" (finishReason={finish_reason})" if finish_reason else "")
            )
            raise ProviderMalformedResponseError(msg) from None

        judgment = judgment.model_copy(
            update={
                "model_name": self.model_name,
                "provider_name": self.provider_name,
            }
        )
        return {
            "judgment": judgment,
            "finish_reason": finish_reason,
            "usage_metadata": usage,
            "raw_response_chars": len(raw_text),
            "raw_response_head": raw_text[:500],
            "raw_response_tail": raw_text[-500:] if len(raw_text) > 500 else raw_text,
        }

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        _ = canary_payload
        return ProviderProbeResult(
            success=True,
            provider_name=self.provider_name,
            model_name=self.model_name,
            metadata={"mode": "spike-local-vertex-adc"},
        )
