# V2-028 Implementer Result

**Task:** Real Vertex Provider Implementation  
**Status:** Implementation complete — awaiting verifier  
**Date:** 2026-07-10

## Summary

Replaced the Task 13 `VertexProvider` stub with a real Gemini REST client that implements `JudgmentProvider`. The adversarial eval probe now delegates to `VertexProvider` instead of a separate `GeminiJudgmentProvider` class in `evals/`.

## Files Changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/vertex_provider.py` | Real Vertex/Gemini provider: `generate_judgment`, `probe`, typed fault mapping (unavailable/timeout/malformed/refusal), shared `judgment_prompt_from_request` and `extract_gemini_candidate_text` helpers |
| `evals/real_provider_adversarial.py` | Removed duplicate `GeminiJudgmentProvider`; `resolve_real_provider()` returns `VertexProvider` |
| `tests/judgment/test_vertex_provider.py` | New mocked tests for Protocol conformance, all four fault types, probe success/failure |
| `tests/judgment/test_provider_failures.py` | Updated unconfigured stub test to expect `status=unconfigured` |
| `tests/evals/test_real_provider_adversarial.py` | Renamed Gemini tests to Vertex; imports from `praetor.judgment.vertex_provider` |
| `docs/eval_gates.md` | Documented `VertexProvider` as live probe backend |

## Acceptance Criteria

| AC | Evidence |
|----|----------|
| Vertex/Gemini provider implements existing Protocol | `VertexProvider` satisfies `JudgmentProvider`; `test_vertex_provider_implements_protocol_unconfigured`, `test_vertex_provider_happy_path_overrides_model_and_provider_names` |
| Synthetic canary probe supported; rate-limited by breaker | `probe()` accepts canary payload and makes lightweight API call; breaker rate-limiting unchanged in `test_provider_health_breaker.py::test_probe_rate_limited` |
| Network tests marker-gated; default suite uses mocks | Integration test retains `@pytest.mark.integration` + `@pytest.mark.probabilistic`; 69 deterministic tests pass with mocked `urllib.request.urlopen` |
| Unavailable/timeout/malformed/refusal map to documented faults | `ProviderUnavailableError` (HTTP 503, URLError), `ProviderTimeoutError` (HTTP 504, socket timeout), `ProviderMalformedResponseError` (missing candidate), `ProviderRefusalError` (SAFETY finishReason, prompt block) |

## Verification

```text
pytest tests/judgment/ tests/evals/test_real_provider_adversarial.py -q
69 passed, 1 deselected in 4.45s
```

(1 deselected = `@pytest.mark.integration` + `@pytest.mark.probabilistic` live probe)

## Design Notes

- **Unconfigured behavior:** `VertexProvider` without `api_key` raises `ProviderUnavailableError` on `generate_judgment` and returns `success=False` with `metadata.status=unconfigured` on `probe`.
- **Probe semantics:** `probe()` catches all `ProviderError` subclasses and returns `success=False` rather than raising, so the provider-health breaker can record probe failures without aborting the transaction.
- **API surface:** Uses Gemini Developer API (`generativelanguage.googleapis.com`) with API key auth; `provider_name` remains `"vertex"` per project convention.
- **Env resolution:** `PRAETOR_GEMINI_API_KEY` or `GOOGLE_API_KEY` + optional `PRAETOR_GEMINI_MODEL` (unchanged from Task 27).

## Unresolved

None.

## Queue Status

Queue item **not** marked done per packet instructions.
