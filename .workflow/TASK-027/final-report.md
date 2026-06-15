# Final Report: TASK-027 (gatekeeper reopen)

## Summary

Gatekeeper reopen closed: evals in mypy gate, mocked Gemini deterministic tests, structural preconditions read from sent payload (with truncation fixture), structural raw_source key walk, and docs deliverable (`docs/decisions.md` DEC-047 + `docs/eval_gates.md`).

## Files changed

- `evals/real_provider_adversarial.py` — payload-driven structural checks, truncated fixture, `_extract_candidate_text`
- `tests/evals/test_real_provider_adversarial.py` — 7 new deterministic tests (14 total deterministic)
- `evals/harness.py` — mypy TypedDict + cast fixes
- `pyproject.toml` — `evals` in mypy packages, `types-PyYAML` dev dep, ruff ignore for `tests/evals`
- `src/praetor/config/loader.py` — remove stale yaml type ignores
- `docs/decisions.md` — DEC-047
- `docs/eval_gates.md` — structural vs probabilistic distinction
- `memory-bank/{tasks,activeContext,progress}.md`
- `.workflow/TASK-027/*`

## Verification performed

```
python -m pytest -q tests/evals/test_real_provider_adversarial.py -m "not integration and not probabilistic"
14 passed, 1 deselected in 0.26s

python -m pytest -q
629 passed, 1 deselected in 49.63s

python -m mypy src evals consumer_sdk
Success: no issues found in 102 source files

python -m ruff check src tests consumer_sdk evals
All checks passed!
```

## Docs deliverable

- `docs/decisions.md` DEC-047: Task 14 deterministic structural isolation vs Task 27 probabilistic probe
- `docs/eval_gates.md`: operator-facing gate reference with CI behavior and manual probe instructions
- `docs/spec.md` not modified (frozen this phase)

## Known gaps

- Live Gemini probe not run in verification (requires API key + `PRAETOR_REAL_PROVIDER_PROBE=1`)
- `tests/evals/__init__.py` omitted to avoid shadowing top-level `evals` package under pytest import path

## safe_to_commit

yes — full gate re-verified 2026-06-13 (gatekeeper reopen)
