"""Vertex/Gemini judgment provider implementing the Task 13 provider Protocol."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from praetor.contracts.judgment import ModelJudgment
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderProbeResult,
    ProviderRefusalError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    parse_model_judgment_json,
)

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_TIMEOUT_SECONDS = 60.0
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

REFUSAL_FINISH_REASONS = frozenset(
    {"SAFETY", "RECITATION", "BLOCKED", "PROHIBITED_CONTENT"}
)
TIMEOUT_HTTP_CODES = frozenset({408, 504})


@dataclass(frozen=True)
class VertexProvider:
    model_name: str = DEFAULT_GEMINI_MODEL
    api_key: str | None = None
    provider_name: str = "vertex"
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        prompt = judgment_prompt_from_request(request)
        raw_json = self._call_generate_content(prompt)
        judgment = parse_model_judgment_json(raw_json)
        return judgment.model_copy(
            update={
                "model_name": self.model_name,
                "provider_name": self.provider_name,
            }
        )

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        if self.api_key is None:
            return ProviderProbeResult(
                success=False,
                provider_name=self.provider_name,
                model_name=self.model_name,
                metadata={
                    "status": "unconfigured",
                    "canary_seen": bool(canary_payload),
                },
            )
        try:
            prompt = json.dumps({"canary_probe": dict(canary_payload)}, sort_keys=True)
            self._call_generate_content(prompt)
        except ProviderError:
            return ProviderProbeResult(
                success=False,
                provider_name=self.provider_name,
                model_name=self.model_name,
                metadata={"canary_seen": bool(canary_payload)},
            )
        return ProviderProbeResult(
            success=True,
            provider_name=self.provider_name,
            model_name=self.model_name,
            metadata={"canary_seen": bool(canary_payload)},
        )

    def _call_generate_content(self, prompt: str) -> str:
        api_key = self._require_api_key()
        url = (
            f"{GEMINI_API_BASE}/{self.model_name}:generateContent"
            f"?key={api_key}"
        )
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                payload_raw = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            msg = f"vertex request timed out after {self.timeout_seconds}s"
            raise ProviderTimeoutError(msg) from exc
        except urllib.error.HTTPError as exc:
            if exc.code in TIMEOUT_HTTP_CODES:
                detail = exc.read().decode("utf-8", errors="replace")
                msg = f"vertex HTTP {exc.code}: {detail[:500]}"
                raise ProviderTimeoutError(msg) from exc
            detail = exc.read().decode("utf-8", errors="replace")
            msg = f"vertex HTTP {exc.code}: {detail[:500]}"
            raise ProviderUnavailableError(msg) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                msg = f"vertex transport timeout: {exc.reason}"
                raise ProviderTimeoutError(msg) from exc
            reason = str(exc.reason)
            if "timed out" in reason.lower():
                msg = f"vertex transport timeout: {reason}"
                raise ProviderTimeoutError(msg) from exc
            msg = f"vertex transport error: {reason}"
            raise ProviderUnavailableError(msg) from exc

        if not isinstance(payload_raw, dict):
            msg = "vertex response was not a JSON object"
            raise ProviderMalformedResponseError(msg)

        return extract_gemini_candidate_text(payload_raw)

    def _require_api_key(self) -> str:
        if not self.api_key:
            msg = (
                "Vertex provider not configured for live calls; "
                "set PRAETOR_GEMINI_API_KEY or GOOGLE_API_KEY"
            )
            raise ProviderUnavailableError(msg)
        return self.api_key


def judgment_prompt_from_request(request: JudgmentRequest) -> str:
    return json.dumps(
        {
            "scenario_id": request.scenario_id,
            "payload": request.payload,
            "task": (
                "Return JSON validating as praetor.contracts.judgment.ModelJudgment. "
                "Use only evidence IDs and field paths present in prompt_excerpt_set."
            ),
        },
        sort_keys=True,
    )


def extract_gemini_candidate_text(payload: Mapping[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        prompt_feedback = payload.get("promptFeedback")
        if isinstance(prompt_feedback, Mapping):
            block_reason = prompt_feedback.get("blockReason")
            if isinstance(block_reason, str) and block_reason:
                msg = f"vertex blocked prompt: {block_reason}"
                raise ProviderRefusalError(msg)
        msg = "vertex response missing candidate text"
        raise ProviderMalformedResponseError(msg)

    first = candidates[0]
    if not isinstance(first, Mapping):
        msg = "vertex response missing candidate text"
        raise ProviderMalformedResponseError(msg)

    finish_reason = first.get("finishReason")
    if isinstance(finish_reason, str) and finish_reason in REFUSAL_FINISH_REASONS:
        msg = f"vertex refused judgment: finishReason={finish_reason}"
        raise ProviderRefusalError(msg)

    content = first.get("content")
    if not isinstance(content, Mapping):
        msg = "vertex response missing candidate text"
        raise ProviderMalformedResponseError(msg)
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        msg = "vertex response missing candidate text"
        raise ProviderMalformedResponseError(msg)
    first_part = parts[0]
    if not isinstance(first_part, Mapping):
        msg = "vertex response missing candidate text"
        raise ProviderMalformedResponseError(msg)
    text = first_part.get("text")
    if not isinstance(text, str):
        msg = "vertex candidate text was not a string"
        raise ProviderMalformedResponseError(msg)
    return text.strip()
