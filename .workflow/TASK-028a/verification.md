# Verification: TASK-028a

## Commands

```bash
python -m pytest -q
python -m evals.harness
python -m mypy src evals consumer_sdk
python -m ruff check src tests consumer_sdk evals
git check-ignore -v tmp-idem.db
```

## Results (2026-06-15, gatekeeper cleanup)

| Check | Result |
|---|---|
| Full pytest | **654 passed**, 1 deselected |
| Eval harness | **25/25 PASS** |
| mypy | Success — 110 files |
| ruff | All checks passed |
| `git check-ignore tmp-idem.db` | `.gitignore:12:tmp-*.db` |

## Focused evidence

```
tests/engine/test_intake_stamp_actuation.py — stamp ordering + deferred persist never-contain conflict
tests/metrics/test_orchestrator_metrics.py — no metrics on in-flight stamp
tests/evals/test_eval_harness.py — directive expectation guard + teeth test
evals/harness.py — engine_intake directive DB assertions + runner key guard
.gitignore — tmp-*.db pattern
src/praetor/policy/gate.py — DeferredDirectivePersistConflict
src/praetor/engine/orchestrator.py — in-band escalate on deferred persist conflict
```
