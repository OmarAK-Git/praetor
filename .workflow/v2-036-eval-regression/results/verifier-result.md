# Verifier Result — V2-036 Eval Regression Locking Discipline

**Verdict: SURVIVES** (claim of completion holds against adversarial checks)

Role: adversarial skeptic-verifier. I re-ran everything myself and did not rely on the implementer's transcript.

## Claim restated

The task delivered (1) a workflow template that requires every confirmed model error to cite a harness scenario or explicit waiver, (2) eval-gate docs defining minimum scenario quality and expectation-key validation, (3) a CI guard that catches stale/unknown expectation keys, scoped to V2-036, with `pytest tests/evals/ -q` green.

## Evidence gathered

### Command (as specified)

```
python -m pytest tests/evals/ -q
→ 132 passed, 1 deselected in 22.32s (exit 0)
```

Matches the implementer's claim (`132 passed, 1 deselected`) exactly.

### AC1 — Workflow template requires model error → scenario or waiver — CONFIRMED

- `.workflow/_template/plan.md`: `REQ-EVAL-REG`, `AC-EVAL-REG`, and `TASK-EVAL-REG` all present, requiring each confirmed model error to cite `evals/scenarios/<scenario_id>.yaml` or a waiver decision ID.
- `.workflow/_template/final-report.md`: "Confirmed model errors (eval regression locking)" section with a table (error → harness scenario → waiver) and a waiver-only-when-infeasible rule.
- `.workflow/_template/review.md`: spec-compliance checklist item enforcing REQ-EVAL-REG.

### AC2 — Docs define minimum scenario quality + expectation-key validation — CONFIRMED

`docs/eval_gates.md` § "Eval harness regression locking (V2-036)" (lines 85–127): 6-point "Minimum scenario quality" list and an "Expectation-key validation" subsection covering unknown / stale / nested keys, with the fail-closed rationale.

### AC3 — CI catches stale or unknown expectation keys — CONFIRMED (wired, not vacuous)

- `evals/harness.py::_validate_expectations` is invoked by `load_scenario` (harness.py:308–314), which raises `ValueError` on any error, and `list_mandatory_scenarios` loads every scenario file — so a real bad key in a scenario file fails at load time.
- `tests/evals/test_expectation_key_validation.py`: 36 tests pass (33 mandatory-scenario params + registry completeness + 3 negative cases).
- Adversarial direct-call against the *imported production* validator (not test-local):
  - `unknown expectation key: 'bogus_key'` (engine_intake)
  - `expectation key 'metrics' is not consumed by runner 'duplicate_retry'`
  - `unknown runner for expectation validation: 'nope'`
  Negative tests exercise the real code path and produce genuine errors.

## Attempts to refute (all failed)

- **Vacuous negative tests?** No — re-invoking the imported `_validate_expectations` reproduced the unknown/stale/unknown-runner errors independently.
- **Guard not wired into loading?** No — `load_scenario` calls it and raises; mandatory scenarios all route through it.
- **Stale evidence?** No — I re-ran `pytest tests/evals/ -q` fresh (132 passed) and the targeted file fresh (36 passed).

## Caveats / limitations

- **AC4 (V2-036 scope only): partially verifiable.** The working tree is heavily modified by many prior uncommitted tasks (v2-015…v2-035), so I could not isolate this task's diff via git. The files the implementer reports (`.workflow/_template/*.md`, `docs/eval_gates.md`, `evals/harness.py`, `tests/evals/test_expectation_key_validation.py`) and their contents are all consistent with V2-036 scope; I found no out-of-scope behavior change in them. No independent contradiction found, but scope isolation could not be positively proven from the tree.
- **Observation (non-blocking):** all three `.workflow/_template/*.md` files store their markdown with every line prefixed by `# ` and headers `\#`-escaped (effectively commented-out). The required requirement text is present regardless, so the acceptance criterion ("template requires…") is satisfied, but the template rendering is odd and may warrant a cleanup follow-up.

## Verdict

**SURVIVES.** The specified command is green on a fresh run, all three substantive acceptance criteria are backed by re-verified evidence, and the CI guard is genuinely wired and non-vacuous. Scope-only (AC4) is consistent with the reported files but not fully isolable from the dirty working tree.
