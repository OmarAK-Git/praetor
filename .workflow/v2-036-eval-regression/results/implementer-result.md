# Implementer Result — V2-036 Eval Regression Locking Discipline

## Files changed

| File | Rationale |
|---|---|
| `.workflow/_template/plan.md` | REQ-EVAL-REG requires confirmed model errors cite harness scenario or waiver |
| `.workflow/_template/final-report.md` | Confirmed model errors table template (scenario path or waiver ID) |
| `.workflow/_template/review.md` | Spec compliance checklist item for eval regression locking |
| `docs/eval_gates.md` | Minimum scenario quality, expectation-key validation rules, CI/workflow discipline |
| `evals/harness.py` | Exported `RUNNER_EXPECTATION_KEYS` / `ALL_EXPECTATION_KEYS`; nested block key validation |
| `tests/evals/test_expectation_key_validation.py` | CI guard for stale/unknown expectation keys across mandatory scenarios |

## Design summary

### Workflow template (eval regression locking)

- Plan template adds **REQ-EVAL-REG** and **AC-EVAL-REG**: every confirmed model error must cite `evals/scenarios/<scenario_id>.yaml` or an explicit waiver decision ID.
- Final-report template adds a **Confirmed model errors** table (error → scenario path → waiver).
- Review template adds a spec-compliance check for the same requirement.

### Eval gate documentation

- New **Eval harness regression locking (V2-036)** section in `docs/eval_gates.md` documents minimum scenario quality (schema, runner, escalate block completeness, Outcome Matrix alignment), expectation-key validation rules (unknown/stale/nested), CI location, and workflow discipline.

### Harness expectation-key registry

- `RUNNER_EXPECTATION_KEYS` and `ALL_EXPECTATION_KEYS` are module-level exports for CI and docs reference.
- `revocation_feed_degraded_mode` nested `auto_contain` / `standard_review` blocks now reject unknown nested keys via `REVOCATION_OUTCOME_BLOCK_KEYS`.

### CI guard

- `tests/evals/test_expectation_key_validation.py` parametrizes all mandatory scenarios through `_validate_expectations`, plus negative cases for unknown top-level keys, stale wrong-runner keys, and stale nested revocation keys.

## Verification

```bash
pytest tests/evals/ -q
```

```
132 passed, 1 deselected in 23.99s
```

## Acceptance mapping

| Criterion | Evidence |
|---|---|
| Workflow template requires confirmed model errors → harness scenario or waiver | `.workflow/_template/plan.md` REQ-EVAL-REG; `final-report.md` table; `review.md` checklist |
| Eval gate docs define minimum scenario quality + expectation-key validation | `docs/eval_gates.md` § Eval harness regression locking (V2-036) |
| CI catches stale or unknown expectation keys | `tests/evals/test_expectation_key_validation.py`; `evals/harness.py` `_validate_expectations` |

## Unresolved / deferred

- Queue **not** marked done (per task instructions).
- No new harness scenarios added in this task (discipline is procedural/template; existing scenarios already pass validation).
