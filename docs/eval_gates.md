# Eval gates

This document distinguishes deterministic eval evidence from probabilistic probes.

## Structural prompt isolation (Task 14) — deterministic

**What it proves**

- `raw_source` never appears in provider-facing payload keys or values
- Every excerpt text is at most `MAX_PROMPT_EXCERPT_CHARS` (200)
- Truncated excerpts set `incomplete=true` and include exact `[...omitting N characters]` markers

**Where it runs**

- `tests/judgment/test_prompt_isolation.py`
- Mandatory harness scenario `prompt_construction_isolation` (`evals/scenarios/prompt_construction_isolation.yaml`)

**CI behavior**

- Included in default `pytest -q`
- Failure blocks merge

## Real-provider adversarial excerpt probe (Task 27) — probabilistic

**What it exercises**

- Instruction-like text embedded in normalized, excerpt-eligible fields (e.g. `command_line`) that survives Task 14 sanitization
- Optional live Gemini call when `PRAETOR_REAL_PROVIDER_PROBE=1` and an API key is configured

**What it does not prove**

- That a live model will resist prompt injection on every run
- That containment or disposition outcomes are safe under adversarial model behavior

**Where it runs**

- `evals/real_provider_adversarial.py`
- `tests/evals/test_real_provider_adversarial.py` (integration test marked `@pytest.mark.integration` and `@pytest.mark.probabilistic`)

**CI behavior**

- Default `pytest` excludes `integration` and `probabilistic` markers
- Deterministic unit tests (mocked Gemini path, structural pre-checks) run in CI
- Live probe results are logged for operator review only

**Manual live run**

```powershell
$env:PRAETOR_REAL_PROVIDER_PROBE = "1"
$env:PRAETOR_GEMINI_API_KEY = "<key>"
python -m evals.real_provider_adversarial
```

See also `docs/decisions.md` DEC-047.

## Phase gates (release checklist)

Phase gates aggregate task-level evidence. Run from repo root after `pip install -e ".[dev]"`.

### Phase 1 — Durable walking skeleton (Tasks 1–12)

```powershell
python -m pytest -q
python -m mypy src
python -m ruff check src tests
python -m pytest -q tests/benchmarks/test_smoke_benchmark.py
```

Pass: contracts exported, WAL + singleton enforced, lifecycle/outboxes operational, smoke benchmark runs against provisional targets, recovery never emits containment.

### Phase 2 — Judgment and policy (Tasks 13–27)

```powershell
python -m evals.harness
python -m pytest -q tests/evals/
python -m pytest -q tests/policy/ tests/judgment/ tests/metrics/
```

Pass: mandatory eval scenarios, Outcome Matrix completeness, reference consumer verifier, adversarial probe documented as probabilistic (above). Production intake integration validated at Task 28a / Phase 3.

### Phase 3 — Correlation (Tasks 28–31)

```powershell
python -m evals.run_phase3_gate
python -m evals.correlation_gate
python -m pytest -q tests/correlation/ tests/evals/test_phase3_regression_gate.py
```

Pass: identity compliance on real fixtures, correlation accuracy gate, citation-anchored host targeting, PolicyGate wired into intake with deferred directive persist.

### Phase 4 — Detection portability (Tasks 32–33)

```powershell
python tools/compile_sigma.py --check
python -m pytest -q tests/detections/ tests/splunk/
```

Pass: Sigma validation, deterministic SPL, Splunk demo artifacts with checksum-verified fixtures.

### Phase 5 — Operator readiness (Tasks 34–35)

```powershell
python -m pytest -q tests/codification/
python -m pytest -q tests/benchmarks/test_serialized_path.py
python -m pytest -q tests/docs/
python -m evals.run_phase5_benchmark
```

The benchmark step is self-contained: it creates a temporary DB, activates
``configs/example_org.yaml``, runs 30 DEC-053 production-path iterations, and
prints sustained rate vs the active provisional targets. No pre-existing
``state/bench.db`` is required.

Pass: org-config sweep produces review-only proposed artifacts; production throughput ceiling measured and documented in `docs/operator_runbook.md`; operator runbook and architecture cover responsibility boundaries; Splunk demo is manual-only per `splunk/README.md` (no automated saved-search CI gate).
