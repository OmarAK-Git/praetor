# Verifier result — eval-kernel-01-scorecard (Task 1)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `scorecard_schema.json` has `additionalProperties` false and the spec §4 required fields | **met** | `evals/schemas/scorecard_schema.json:6` is `additionalProperties: false`. Required list (`schema_version`, `scenario_id`, `realm`, `arm`, `status`, `failure_class`, `expected`, `observed`, `provider`) matches spec §4 scorecard table in `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md:92-103`. Optional `notes` is present and not required. Enums/const match the table (`schema_version` `"1"`; realms; arms; statuses; failure classes; providers). Working tree identical to commit `204c0d4`. |
| `ScorecardRow` rejects unknown fields | **met** | `evals/scorecard.py:25` `ConfigDict(extra="forbid")`. `test_row_rejects_unknown_field` passed. Independent probe: `skip_reason` → `ValidationError`. |
| `pending` is legal only for `cap.baseline_bag_path_a` and `cap.stump_parity_guard` `new_build` | **met** | `CAPABILITY_QUALITY_IDS` + `arm == "new_build"` in `evals/scorecard.py:15-17,40-50`. Pytest: `test_pending_legal_only_for_capability_quality_new_build` passed (validates `cap.baseline_bag_path_a` new_build). Independent probe: `cap.stump_parity_guard` new_build pending accepted; same IDs on `old_build` raise `ScorecardValidationError`. |
| `pending` is illegal for `cap.no_label_leak_ids` and non-capability rows | **met** | `test_pending_illegal_for_leak_pin_and_non_quality` passed (leak pin + default governance payload). Validator rejects any pending row outside the quality-id × new_build pair. |
| `failure_class` is `none` when pass or pending, and not `none` when fail or error | **met** | `evals/scorecard.py:51-56`. Pytest: pass+`model` rejected; fail+`none` rejected; error+`harness` accepted. Independent probe: pending+`model` rejected; error+`none` rejected; fail+`model` accepted. |
| Verifier checks only Task 1 acceptance, not Sprint 1 gate completion | **met** | Commands limited to packet Task 1 set. No kernel/CI/sprint-exit checks run. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `python -m pytest tests/evals/test_scorecard.py -q` | **0** | `......` — 6 passed in 0.12s |
| `python -m ruff check evals/scorecard.py tests/evals/test_scorecard.py` | **0** | All checks passed |
| `python -m mypy evals/scorecard.py` | **0** | Success: no issues found in 1 source file |

These were re-run in this session against the current working tree (identical to `204c0d4` for the three Task 1 files). Implementer transcript was not treated as evidence.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| No `src/praetor/` edits | **met** | `git show --name-status 204c0d4` lists only `evals/schemas/scorecard_schema.json`, `evals/scorecard.py`, `tests/evals/test_scorecard.py`. `git status --short -- src/praetor` empty. |
| No `evals/harness.py` edits | **met** | Same commit file list; `git status --short -- evals/harness.py` empty. Uncommitted `evals/` / `src/` / `tests/` empty. |

Commit inspected: `204c0d4d7754ebf8d2943486a4f1a8ae8e459a9c` (`feat(evals): add E2E scorecard schema and pending rules`).

## Independent probes (not in packet)

Used only to close test-coverage holes; all behaved as specified:

- `cap.stump_parity_guard` + `new_build` + `pending` + `failure_class=none` → accepted
- quality IDs + `old_build` + `pending` → `ScorecardValidationError`
- legal pending + `failure_class=model` → `ScorecardValidationError`
- `status=error` + `failure_class=none` → `ScorecardValidationError`
- `status=fail` + `failure_class=model` → accepted
- unknown field `skip_reason` → `ValidationError`

## Gaps

None that fail Task 1 acceptance.

Residual (non-blocking): unit tests do not themselves call `validate_scorecard_row` for `cap.stump_parity_guard` pending, pending+non-`none` `failure_class`, or `error`+`none`. Implementation and independent probes cover those cases.
