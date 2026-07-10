# V2-028 Verifier Result — Real Vertex Provider Implementation

**Verdict:** SURVIVES (pass)
**Date:** 2026-07-10
**Method:** Adversarial re-verification from a fresh context. Ran the task-scoped
command myself; read the implementation, tests, spec, and marker config directly.
Did not rely on the implementer transcript as evidence.

## Claim Under Test

Implementer claims V2-028 complete: real `VertexProvider` implements the Task 13
`JudgmentProvider` Protocol, canary probe supported and breaker rate-limited,
network tests marker-gated (default suite uses mocks), and the four fault types
map to documented errors. Cited evidence: `pytest tests/judgment/
tests/evals/test_real_provider_adversarial.py -q` → 69 passed, 1 deselected.

## Evidence Gathered

### Verification command (reproduced)
```text
python -m pytest tests/judgment/ tests/evals/test_real_provider_adversarial.py -q
69 passed, 1 deselected in 4.39s   (exit 0)
```
Matches the claimed count exactly. Output was all `.` — no silent skips (`s`),
no xfails. Reproduced independently, not copied from the transcript.

### AC1 — Provider implements existing Protocol
- `VertexProvider` (`src/praetor/judgment/vertex_provider.py:36`) exposes
  `generate_judgment` and `probe` matching `JudgmentProvider`
  (`src/praetor/judgment/provider.py:72`).
- `test_vertex_provider_implements_protocol_unconfigured` asserts
  `isinstance(provider, JudgmentProvider)`. Note: `JudgmentProvider` is
  `@runtime_checkable`, so `isinstance` only checks method *presence* — but
  `test_vertex_provider_happy_path_overrides_model_and_provider_names` supplies
  genuine behavioral conformance (real `generate_judgment` call returns a valid
  `ModelJudgment` with overridden `model_name`/`provider_name`). Not gamed.

### AC2 — Canary probe supported; breaker rate-limited
- `probe()` (`vertex_provider.py:53`) accepts a canary mapping; unconfigured →
  `success=False, metadata.status=unconfigured`; configured → lightweight call.
- Breaker rate-limit test cited by implementer is real and passes within the 69:
  `tests/judgment/test_provider_health_breaker.py::test_probe_rate_limited`
  (line 271), plus `test_probe_rate_limit_rollover_after_minute` (line 529).
  The breaker consumes any `probe()`-conforming provider, so `VertexProvider`
  is rate-limited by construction.

### AC3 — Network tests marker-gated; default suite mocked
- `pyproject.toml:32` → `addopts = '-m "not integration and not probabilistic"'`;
  markers declared at lines 29–30. The 1 deselected test is the only live probe
  (`test_adversarial_probe_logs_results_when_enabled`, marked
  `@pytest.mark.integration` + `@pytest.mark.probabilistic`).
- All deterministic tests patch `urllib.request.urlopen` or use fakes; no real
  network egress in the default suite. Confirmed by reading every test in
  `tests/judgment/test_vertex_provider.py` and the Vertex tests in
  `tests/evals/test_real_provider_adversarial.py`.

### AC4 — Fault mapping (unavailable / timeout / malformed / refusal)
Each mapping is exercised by a test that patches the network layer and asserts
on the exception actually raised by the implementation (not a stubbed value):
- Unavailable: HTTP 503 → `ProviderUnavailableError`; `URLError("connection reset")`
  → `ProviderUnavailableError` (`vertex_provider.py:105-122`).
- Timeout: HTTP 504 → `ProviderTimeoutError`; `URLError(socket.timeout)` →
  `ProviderTimeoutError` (`vertex_provider.py:102-120`, `TIMEOUT_HTTP_CODES`).
- Malformed: empty `candidates` and non-string `text` → `ProviderMalformedResponseError`
  (`vertex_provider.py:154-192`).
- Refusal: `finishReason=SAFETY` and `promptFeedback.blockReason` →
  `ProviderRefusalError` (`vertex_provider.py:157-174`).

### Cleanup / de-duplication claim
- No `GeminiJudgmentProvider` remains in `src/` or `tests/` (only in
  memory-bank/docs history). `evals/real_provider_adversarial.py:272`
  `resolve_real_provider()` returns `VertexProvider`.
- `docs/eval_gates.md:28` documents `VertexProvider` as the live probe backend.

## Gaps / Non-blocking Observations

1. **Generic HTTP 5xx → Unavailable.** Any non-408/504 `HTTPError` (e.g. 500)
   maps to `ProviderUnavailableError`. The spec only enumerates
   unavailable/timeout/malformed/refusal, so this is within intent, but a 500
   "server error" is arguably distinct from "unavailable." Not a refutation.
2. **Protocol conformance via runtime_checkable isinstance** checks method names
   only; behavioral conformance is covered separately (see AC1). Acceptable.

Neither observation blocks completion; both are documented-fault-consistent.

## Conclusion

The completion claim **survives** adversarial verification. The task-scoped
command passes reproducibly (69 passed, 1 deselected), all four acceptance
criteria are backed by tests that exercise the real implementation through a
patched network boundary, marker gating keeps live calls out of default CI, and
the Task 13 stub / duplicate `GeminiJudgmentProvider` were genuinely removed.
