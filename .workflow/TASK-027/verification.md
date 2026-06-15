# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–006 | Deterministic probe tests | `python -m pytest -q tests/evals/test_real_provider_adversarial.py -m "not integration and not probabilistic"` | pass | 14 passed, 1 deselected | pass |
| VERIFY-002 | REQ-005 | Default pytest excludes probabilistic | `python -m pytest -q --collect-only tests/evals/test_real_provider_adversarial.py` | integration test deselected | 14/15 collected (1 deselected) | pass |
| VERIFY-003 | AC-003 | Full regression | `python -m pytest -q` | pass | 629 passed, 1 deselected | pass |
| VERIFY-004 | AC-003 | mypy | `python -m mypy src evals consumer_sdk` | clean | 102 source files clean | pass |
| VERIFY-005 | AC-003 | ruff | `python -m ruff check src tests consumer_sdk evals` | clean | All checks passed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live Gemini adversarial run | Requires `PRAETOR_REAL_PROVIDER_PROBE=1` + API key; non-deterministic | Manual operator probe only; documented in `docs/eval_gates.md` |
