"""V2-028 Vertex/Gemini provider Protocol conformance and fault mapping."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from praetor.engine.skeleton import skeleton_model_judgment
from praetor.judgment.provider import (
    JudgmentProvider,
    JudgmentRequest,
    ProviderMalformedResponseError,
    ProviderRefusalError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from praetor.judgment.vertex_provider import VertexProvider


def _urlopen_mock(response_body: dict[str, object]) -> MagicMock:
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_body).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return MagicMock(return_value=mock_response)


def test_vertex_provider_implements_protocol_unconfigured() -> None:
    provider: JudgmentProvider = VertexProvider(model_name="gemini-test")

    assert isinstance(provider, JudgmentProvider)
    result = provider.probe({"canary": "synthetic"})
    assert result.success is False
    assert result.provider_name == "vertex"
    assert result.metadata["status"] == "unconfigured"
    assert result.metadata["canary_seen"] is True


def test_vertex_provider_unconfigured_raises_unavailable() -> None:
    provider = VertexProvider(model_name="gemini-test")

    with pytest.raises(ProviderUnavailableError, match="not configured"):
        provider.generate_judgment(JudgmentRequest(scenario_id="unconfigured"))


def test_vertex_provider_happy_path_overrides_model_and_provider_names() -> None:
    request = JudgmentRequest(scenario_id="valid", payload={"evidence": []})
    judgment_json = skeleton_model_judgment().model_dump_json()
    provider = VertexProvider(api_key="test-key", model_name="gemini-test-model")
    mock_urlopen = _urlopen_mock(
        {"candidates": [{"content": {"parts": [{"text": judgment_json}]}}]}
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        judgment = provider.generate_judgment(request)

    assert judgment.model_name == "gemini-test-model"
    assert judgment.provider_name == "vertex"


def test_vertex_provider_http_error_raises_unavailable() -> None:
    provider = VertexProvider(api_key="test-key")
    http_error = urllib.error.HTTPError(
        url="https://example.test",
        code=503,
        msg="Service Unavailable",
        hdrs={},
        fp=BytesIO(b"upstream unavailable"),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderUnavailableError, match="503"):
            provider.generate_judgment(JudgmentRequest(scenario_id="http-error"))


def test_vertex_provider_http_timeout_code_raises_timeout() -> None:
    provider = VertexProvider(api_key="test-key")
    http_error = urllib.error.HTTPError(
        url="https://example.test",
        code=504,
        msg="Gateway Timeout",
        hdrs={},
        fp=BytesIO(b"gateway timeout"),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderTimeoutError, match="504"):
            provider.generate_judgment(JudgmentRequest(scenario_id="http-timeout"))


def test_vertex_provider_url_error_raises_unavailable() -> None:
    provider = VertexProvider(api_key="test-key")
    url_error = urllib.error.URLError("connection reset")

    with patch("urllib.request.urlopen", side_effect=url_error):
        with pytest.raises(ProviderUnavailableError, match="connection reset"):
            provider.generate_judgment(JudgmentRequest(scenario_id="url-error"))


def test_vertex_provider_url_timeout_raises_timeout() -> None:
    provider = VertexProvider(api_key="test-key")
    url_error = urllib.error.URLError(TimeoutError("timed out"))

    with patch("urllib.request.urlopen", side_effect=url_error):
        with pytest.raises(ProviderTimeoutError, match="timed out"):
            provider.generate_judgment(JudgmentRequest(scenario_id="url-timeout"))


def test_vertex_provider_missing_candidate_raises_malformed() -> None:
    provider = VertexProvider(api_key="test-key")
    mock_urlopen = _urlopen_mock({"candidates": []})

    with patch("urllib.request.urlopen", mock_urlopen):
        with pytest.raises(ProviderMalformedResponseError, match="missing candidate"):
            provider.generate_judgment(JudgmentRequest(scenario_id="no-candidate"))


def test_vertex_provider_safety_finish_raises_refusal() -> None:
    provider = VertexProvider(api_key="test-key")
    mock_urlopen = _urlopen_mock(
        {
            "candidates": [
                {
                    "finishReason": "SAFETY",
                    "content": {"parts": [{"text": "{}"}]},
                }
            ]
        }
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        with pytest.raises(ProviderRefusalError, match="SAFETY"):
            provider.generate_judgment(JudgmentRequest(scenario_id="safety-refusal"))


def test_vertex_provider_prompt_block_raises_refusal() -> None:
    provider = VertexProvider(api_key="test-key")
    mock_urlopen = _urlopen_mock(
        {
            "candidates": [],
            "promptFeedback": {"blockReason": "SAFETY"},
        }
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        with pytest.raises(ProviderRefusalError, match="blocked prompt"):
            provider.generate_judgment(JudgmentRequest(scenario_id="prompt-block"))


def test_vertex_provider_non_string_candidate_raises_malformed() -> None:
    provider = VertexProvider(api_key="test-key")
    mock_urlopen = _urlopen_mock(
        {"candidates": [{"content": {"parts": [{"text": 123}]}}]}
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        with pytest.raises(
            ProviderMalformedResponseError,
            match="candidate text was not a string",
        ):
            provider.generate_judgment(JudgmentRequest(scenario_id="bad-text"))


def test_vertex_provider_probe_success_with_canary() -> None:
    provider = VertexProvider(api_key="test-key")
    judgment_json = skeleton_model_judgment().model_dump_json()
    mock_urlopen = _urlopen_mock(
        {"candidates": [{"content": {"parts": [{"text": judgment_json}]}}]}
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        result = provider.probe({"canary": "praetor-provider-health-probe-v1"})

    assert result.success is True
    assert result.provider_name == "vertex"
    assert result.metadata["canary_seen"] is True


def test_vertex_provider_probe_failure_on_api_error() -> None:
    provider = VertexProvider(api_key="test-key")
    http_error = urllib.error.HTTPError(
        url="https://example.test",
        code=503,
        msg="Service Unavailable",
        hdrs={},
        fp=BytesIO(b"upstream unavailable"),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        result = provider.probe({"canary": "probe-fail"})

    assert result.success is False
    assert result.metadata["canary_seen"] is True
