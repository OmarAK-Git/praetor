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
