# Workflow Plan: TASK-027 — Real-Provider Adversarial Excerpt Probe

## Goal

Deliver a probabilistic integration probe that runs adversarial instruction-like excerpts through a real LLM provider, logs observations for human review, and cannot be mistaken for a deterministic safety proof.

## Tier

T3 — Flight Recorder workflow.

## Scope

### In scope

- `evals/real_provider_adversarial.py` — adversarial fixture builder, optional Gemini REST provider, probe runner, structured logging
- `tests/evals/test_real_provider_adversarial.py` — deterministic structural pre-checks + `@pytest.mark.integration` `@pytest.mark.probabilistic` probe
- `pyproject.toml` — register markers; exclude integration/probabilistic from default `pytest` runs
- `.workflow/TASK-027/*` flight recorder artifacts
- Memory Bank updates

### Out of scope

- `docs/` edits (start-task hard limit; gap recorded in review.md)
- VertexProvider live implementation in `src/` (probe owns optional REST client in `evals/`)
- PolicyGate wiring, correlation gates, Task 28+

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Adversarial evidence facts embed instruction-like text in normalized fields that survive structural excerpt sanitization |
| REQ-002 | Probe builds provider payload via Task 14 `build_judgment_prompt_payload`; structural preconditions asserted before live call |
| REQ-003 | Live call uses real provider when `PRAETOR_REAL_PROVIDER_PROBE=1` and API key present; otherwise skips |
| REQ-004 | Integration test marked `@pytest.mark.integration` and `@pytest.mark.probabilistic` |
| REQ-005 | Probabilistic test logs results; does not assert deterministic pass/fail on model behavior |
| REQ-006 | Module docstring distinguishes structural prompt isolation (Task 14) from probabilistic real-provider resistance |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001–006 | `tests/evals/test_real_provider_adversarial.py` deterministic tests pass |
| AC-002 | CI safety | Default `pytest -q` excludes integration/probabilistic markers |
| AC-003 | Regression | Full `pytest -q`, `mypy src`, `ruff check src tests consumer_sdk evals` |

## Implementation Plan

| Task | Description | Files | Status |
|---|---|---|---|
| T-001 | Workflow artifacts | `.workflow/TASK-027/*` | in_progress |
| T-002 | Probe module + Gemini REST client | `evals/real_provider_adversarial.py` | pending |
| T-003 | Tests + pytest markers | `tests/evals/test_real_provider_adversarial.py`, `pyproject.toml` | pending |
| T-004 | Verification + Memory Bank | `memory-bank/*` | pending |

## Risks

- Real provider behavior is non-deterministic by design; probe must never gate CI.
- No `docs/` edit allowed; distinction documented in module docstring and flight recorder.
- Gemini REST requires network + API key; integration test skips when unset.

## Verification plan

- `python -m pytest -q tests/evals/test_real_provider_adversarial.py -m "not integration and not probabilistic"`
- `python -m pytest -q` (default excludes probabilistic/integration)
- `python -m mypy src`
- `python -m ruff check src tests consumer_sdk evals`
