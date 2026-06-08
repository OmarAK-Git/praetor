# Workflow Plan

## Goal

Implement Task 13: introduce a judgment provider abstraction, FakeProvider scenario modes, bounded timeout retry, and a Vertex provider stub so the walking skeleton no longer owns an inline provider protocol.

## Scope

### In scope

- Add `src/praetor/judgment/` with the provider Protocol, provider failure exceptions, retry helper, FakeProvider modes, and Vertex provider stub.
- Wire `src/praetor/engine/orchestrator.py` to depend on the provider Protocol from `praetor.judgment.provider`.
- Translate provider malformed JSON, timeout-after-retry, and refusal failures into Outcome Matrix edicts.
- Keep fabricated citations as provider output that then flows through the existing structural citation validator.
- Add focused tests in `tests/judgment/test_provider_failures.py`.

### Out of scope

- Do not modify `docs/`.
- Do not implement prompt construction or excerpt hygiene from Task 14.
- Do not implement evidence citation validator beyond the existing walking-skeleton validator; Task 15 owns the general validator.
- Do not implement PolicyGate, breakers, rate limits, or half-open probes from later tasks.
- Do not call a real Vertex/Gemini service.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Engine judgment calls depend on a reusable provider Protocol instead of a protocol local to `engine.orchestrator`. |
| REQ-002 | FakeProvider supports valid, malformed JSON, timeout, refusal, and fabricated citation modes. |
| REQ-003 | Provider timeout uses bounded retry with backoff and produces `provider_timeout` after retry exhaustion. |
| REQ-004 | Malformed provider output produces `provider_malformed_json` with `system_fault_escalation=true`. |
| REQ-005 | Provider refusal produces `provider_refusal` with `system_fault_escalation=true`. |
| REQ-006 | Fabricated citations remain scenario-scoped provider output and produce `invalid_model_citation` through the existing citation path. |
| REQ-007 | FakeProvider implements `probe(canary_payload)`. |
| REQ-008 | Vertex provider stub implements the provider Protocol without real network behavior. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `WalkingSkeletonEngine` and `process_alert_intake` annotate `judgment_provider` with `praetor.judgment.provider.JudgmentProvider`. |
| AC-002 | REQ-002 | Tests instantiate FakeProvider in each documented mode and observe mode-specific behavior. |
| AC-003 | REQ-003 | A timeout mode records the configured number of provider attempts and returns an edict with `provider_timeout`. |
| AC-004 | REQ-004 | A malformed JSON mode returns an edict with `provider_malformed_json`. |
| AC-005 | REQ-005 | A refusal mode returns an edict with `provider_refusal`. |
| AC-006 | REQ-006 | A fabricated citation mode returns an edict with `invalid_model_citation`, proving provider output stays separated from citation validation. |
| AC-007 | REQ-007 | A FakeProvider probe test returns a successful probe result and records no production alert data requirement. |
| AC-008 | REQ-008 | A VertexProvider instance is assignable to the Protocol and exposes `generate_judgment` and `probe`. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Add failing Task 13 tests for FakeProvider modes, provider failure edicts, bounded timeout retry, probe, and Vertex stub Protocol conformance. | `tests/judgment/test_provider_failures.py` | complete |
| TASK-002 | Add `praetor.judgment.provider` with Protocol, request/probe dataclasses, provider exceptions, retry policy, and `call_provider_with_retries`. | `src/praetor/judgment/provider.py`, `src/praetor/judgment/__init__.py` | complete |
| TASK-003 | Add FakeProvider modes that emit valid JSON, malformed JSON, timeout, refusal, and fabricated citation outputs. | `src/praetor/judgment/fake_provider.py` | complete |
| TASK-004 | Add VertexProvider stub that implements the Protocol and fails explicitly when used before real integration. | `src/praetor/judgment/vertex_provider.py` | complete |
| TASK-005 | Replace the orchestrator-local provider Protocol and counting provider with the judgment provider layer; add provider failure completion paths. | `src/praetor/engine/orchestrator.py`, `tests/engine/conftest.py`, existing engine tests if imports move | complete |
| TASK-006 | Run scoped tests, full suite, mypy, and ruff; update workflow artifacts and Memory Bank. | `.workflow/TASK-013/*`, `memory-bank/*` | complete |
