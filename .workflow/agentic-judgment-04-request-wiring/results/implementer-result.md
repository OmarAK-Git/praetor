# Implementer result — agentic-judgment-04-request-wiring

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/provider.py` | Added optional `JudgmentRequest.evidence_bundle` field (default `None`) with `EvidenceBundle` import |
| `src/praetor/engine/orchestrator.py` | Pass `resolved_bundle` on `JudgmentRequest` construction in `process_alert_intake` |
| `tests/engine/test_agentic_request_evidence_bundle_wiring.py` | New TDD test: capturing provider receives resolved bundle on intake |
| `tests/judgment/test_provider_failures.py` | Backward-compat test: `JudgmentRequest` without `evidence_bundle` defaults to `None` |

## TDD sequence

1. **Red** — `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py -v`
   - `AttributeError: 'JudgmentRequest' object has no attribute 'evidence_bundle'`
2. **Green** — implemented field + orchestrator wiring; all targeted tests pass

## Verification commands and outcomes

```text
pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py tests/judgment tests/engine -q
→ 144 passed in 16.00s

ruff check src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py tests/engine/test_agentic_request_evidence_bundle_wiring.py
→ All checks passed

mypy src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py
→ Success: no issues found in 2 source files
```

## Gaps / notes

- Test setup mirrors `tests/engine/conftest.py` (`activated` fixture) and `test_gate5_intake_wiring.py` (`SucceedingStampBackend`, `WalkingSkeletonEngine`). Plan's `correlate=False` with explicit bundle would hit correlation-failure path in current `_resolve_intake_evidence_bundle`; test uses default `correlate=True` with `evidence_bundle=` so provider is invoked.
- Single-shot `FakeProvider` / `VertexProvider` unchanged; existing construction sites remain valid via default `None`.
- No commit; queue item not marked done.
