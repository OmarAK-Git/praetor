"""TASK-027 real-provider adversarial excerpt probe tests."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from evals.real_provider_adversarial import (
    INJECTION_MARKER,
    SCENARIO_ID,
    AdversarialProbeResult,
    GeminiJudgmentProvider,
    _provider_prompt_from_request,
    assert_structural_preconditions,
    build_adversarial_evidence_facts,
    build_adversarial_judgment_request,
    build_adversarial_truncated_judgment_request,
    probe_enabled,
    resolve_real_provider,
    run_adversarial_probe,
)

from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.skeleton import skeleton_model_judgment
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderMalformedResponseError,
    ProviderProbeResult,
    ProviderUnavailableError,
)

OMISSION_RE = re.compile(r"\[\.\.\.omitting (?P<count>\d+) characters\]")


class _LoggingCaptureProvider:
    provider_name = "capture"
    model_name = "capture-model"

    def __init__(self, judgment: ModelJudgment) -> None:
        self.judgment = judgment
        self.seen_request: JudgmentRequest | None = None

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.seen_request = request
        return self.judgment

    def probe(self, canary_payload: object) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True,
            provider_name=self.provider_name,
            model_name=self.model_name,
            metadata={"canary_seen": bool(canary_payload)},
        )


def _gemini_urlopen_mock(response_body: dict[str, object]) -> MagicMock:
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_body).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    mock_urlopen = MagicMock(return_value=mock_response)
    return mock_urlopen


def test_adversarial_facts_embed_injection_in_normalized_command_line() -> None:
    facts = build_adversarial_evidence_facts()
    command_line = facts[0]["normalized_fields"]["command_line"]
    assert INJECTION_MARKER in command_line
    assert "raw_source" in facts[0]
    assert "raw_source" in facts[0]["normalized_fields"]


def test_structural_preconditions_read_from_request_payload() -> None:
    request = build_adversarial_judgment_request()
    structural = assert_structural_preconditions(request)

    assert structural.raw_source_excluded is True
    assert structural.excerpt_max_chars_respected is True
    assert structural.injection_present_in_excerpts is True
    assert structural.all_met is True
    assert "prompt_excerpt_set" in request.payload


def test_truncated_fixture_exercises_incomplete_excerpt_from_payload() -> None:
    request = build_adversarial_truncated_judgment_request()
    structural = assert_structural_preconditions(request)
    excerpts = request.payload["prompt_excerpt_set"]["facts"][0]["excerpts"]
    command_excerpt = next(
        item for item in excerpts if item["field_path"] == "normalized_fields.command_line"
    )

    assert structural.raw_source_excluded is True
    assert structural.excerpt_max_chars_respected is True
    assert structural.injection_present_in_excerpts is True
    assert command_excerpt["incomplete"] is True
    assert command_excerpt["omitted_characters"] > 0
    assert OMISSION_RE.search(command_excerpt["text"]) is not None


def test_probe_skipped_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRAETOR_REAL_PROVIDER_PROBE", raising=False)
    monkeypatch.delenv("PRAETOR_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = run_adversarial_probe()

    assert result.provider_called is False
    assert result.skipped_reason is not None
    assert result.structural.all_met is True


def test_resolve_real_provider_returns_none_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PRAETOR_REAL_PROVIDER_PROBE", raising=False)
    assert resolve_real_provider() is None


def test_run_probe_logs_observations_without_asserting_model_outcome() -> None:
    judgment = skeleton_model_judgment(proposed=Disposition.STANDARD_REVIEW)
    provider = _LoggingCaptureProvider(judgment)

    result = run_adversarial_probe(provider=provider)

    assert result.provider_called is True
    assert result.judgment is not None
    assert result.observations
    assert provider.seen_request is not None
    assert provider.seen_request.scenario_id == SCENARIO_ID
    assert "probabilistic probe complete" in "\n".join(result.observations)


def test_format_log_includes_structural_and_provider_fields() -> None:
    request = build_adversarial_judgment_request()
    structural = assert_structural_preconditions(request)
    result = AdversarialProbeResult(
        scenario_id=SCENARIO_ID,
        structural=structural,
        provider_called=True,
        provider_name="gemini",
        model_name="gemini-2.0-flash",
        judgment=skeleton_model_judgment(),
        observations=["example observation"],
    )
    log_text = result.format_log()

    assert "structural_preconditions_met=True" in log_text
    assert "provider_called=True" in log_text
    assert "observation=example observation" in log_text


def test_probabilistic_test_has_required_markers() -> None:
    import tests.evals.test_real_provider_adversarial as module

    test_fn = module.test_adversarial_probe_logs_results_when_enabled
    marker_names = {marker.name for marker in test_fn.pytestmark}
    assert marker_names == {"integration", "probabilistic"}


def test_provider_prompt_carries_scenario_id_and_injection_marker() -> None:
    request = build_adversarial_judgment_request()
    prompt = _provider_prompt_from_request(request)

    assert SCENARIO_ID in prompt
    assert INJECTION_MARKER in prompt


def test_gemini_happy_path_overrides_model_and_provider_names() -> None:
    request = build_adversarial_judgment_request()
    judgment_json = skeleton_model_judgment().model_dump_json()
    provider = GeminiJudgmentProvider(api_key="test-key", model_name="gemini-test-model")
    mock_urlopen = _gemini_urlopen_mock(
        {"candidates": [{"content": {"parts": [{"text": judgment_json}]}}]}
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        judgment = provider.generate_judgment(request)

    assert judgment.model_name == "gemini-test-model"
    assert judgment.provider_name == "gemini"


def test_gemini_http_error_raises_provider_unavailable() -> None:
    request = build_adversarial_judgment_request()
    provider = GeminiJudgmentProvider(api_key="test-key")
    http_error = urllib.error.HTTPError(
        url="https://example.test",
        code=503,
        msg="Service Unavailable",
        hdrs={},
        fp=BytesIO(b"upstream unavailable"),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderUnavailableError, match="503") as exc_info:
            provider.generate_judgment(request)

    assert "503" in str(exc_info.value)


def test_gemini_url_error_raises_provider_unavailable() -> None:
    request = build_adversarial_judgment_request()
    provider = GeminiJudgmentProvider(api_key="test-key")
    url_error = urllib.error.URLError("connection reset")

    with patch("urllib.request.urlopen", side_effect=url_error):
        with pytest.raises(ProviderUnavailableError, match="connection reset"):
            provider.generate_judgment(request)


def test_gemini_missing_candidate_text_raises_malformed_response() -> None:
    request = build_adversarial_judgment_request()
    provider = GeminiJudgmentProvider(api_key="test-key")
    mock_urlopen = _gemini_urlopen_mock({"candidates": []})

    with patch("urllib.request.urlopen", mock_urlopen):
        with pytest.raises(ProviderMalformedResponseError, match="missing candidate text"):
            provider.generate_judgment(request)


def test_gemini_non_string_candidate_text_raises_malformed_response() -> None:
    request = build_adversarial_judgment_request()
    provider = GeminiJudgmentProvider(api_key="test-key")
    mock_urlopen = _gemini_urlopen_mock(
        {"candidates": [{"content": {"parts": [{"text": 123}]}}]}
    )

    with patch("urllib.request.urlopen", mock_urlopen):
        with pytest.raises(
            ProviderMalformedResponseError,
            match="candidate text was not a string",
        ):
            provider.generate_judgment(request)


@pytest.mark.integration
@pytest.mark.probabilistic
def test_adversarial_probe_logs_results_when_enabled(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-deterministic probe: always passes; logs model behavior for review."""
    if not probe_enabled():
        pytest.skip("PRAETOR_REAL_PROVIDER_PROBE not enabled")

    provider = resolve_real_provider()
    if provider is None:
        pytest.skip("no Gemini API key configured")

    with caplog.at_level(logging.INFO):
        result = run_adversarial_probe(provider=provider)
        logging.getLogger("praetor.adversarial_probe").info("%s", result.format_log())

    assert result.structural.all_met is True
    assert result.provider_called is True
    assert isinstance(provider, GeminiJudgmentProvider)
