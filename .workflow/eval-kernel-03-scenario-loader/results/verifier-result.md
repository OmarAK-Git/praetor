# Verifier result — eval-kernel-03-scenario-loader (Task 3)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 3 is done — E2E scenario YAML contract loader (sibling-tree schema, stem must match `scenario_id`, no skip flags, `theater_detector` required, spec §4 fields enforced). Outcome Matrix `scenario_schema.json` untouched.

Implementer result (`done`, pytest 4 / ruff / mypy green, commit `9710405`) was treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| E2E YAML lives under `evals/e2e_scenarios` or a tests fixture tree, not `evals/scenarios` | **met** | Loader fixture is `tests/evals/fixtures/e2e/gov.never_contain_live_shape.yaml`. `evals/e2e_scenarios/` contains only `.gitkeep`. No kernel YAML under `evals/scenarios/`. `list_e2e_scenarios` defaults to `E2E_SCENARIOS_DIR` (`evals/e2e_scenario.py:140-142`). |
| `load_e2e_scenario` rejects stem/id mismatch, missing `theater_detector`, and skip flags | **met** | Stem: `evals/e2e_scenario.py:115-118` + `test_filename_stem_must_match_scenario_id`. Skip: root `additionalProperties: false` + `test_skip_flag_is_rejected`. Missing detector: schema `required` includes `theater_detector` (`evals/schemas/e2e_scenario_schema.json:16`); `_validate_object` emits `missing required field` (`evals/e2e_scenario.py:64-66`). Fresh probe this session: dropping the key → `ValueError` `missing required field: theater_detector`. Empty string → enum reject. |
| Required spec §4 fields are enforced | **met** | Spec §4 scenario contract (`docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md:109-121`): `schema_version`, `scenario_id`, `realm`, `description`, `runner`, `setup`, `arms`, `scorecard_pins`, `theater_detector`. All nine are in schema `required` (`e2e_scenario_schema.json:7-16`). `runner` const `e2e_kernel`. Arms require `old_build`/`new_build` with `expected`+`provider`. Fresh probe: missing `description` → `missing required field: description`. |
| Verifier checks only Task 3 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set plus a loader probe. No sprint-exit, CI, or scenario-execution checks. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/test_e2e_scenario.py -q` | **0** | `....` 4 passed in 0.16s (no skips) |
| `ruff check evals/e2e_scenario.py tests/evals/test_e2e_scenario.py` | **0** | All checks passed |
| `mypy evals/e2e_scenario.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against the current working tree. Implementer transcript was not treated as evidence.

Product files on disk match commit `971040559e06f757e7285c83b93cde4e90299cf1` (`git diff 9710405 --` those four paths empty). Later `84c3033` is workflow-only (implementer result).

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Outcome Matrix `scenario_schema.json` untouched / not in Task 3 commit | **met** | `git show --name-only 9710405` lists only `evals/e2e_scenario.py`, `evals/schemas/e2e_scenario_schema.json`, `tests/evals/test_e2e_scenario.py`, `tests/evals/fixtures/e2e/gov.never_contain_live_shape.yaml`. `git diff 9710405^ 9710405 -- evals/schemas/scenario_schema.json evals/scenarios` empty. Working-tree `git hash-object`, `HEAD:`, and `9710405:` all `4068abebff75f9a70d812dc09ea6444e0f951e2d`. Last dedicated commit on that file is `d086f39` (TASK-026). `git status --short -- evals/schemas/scenario_schema.json evals/scenarios` empty. |
| No CBC JSON or extra envelope fields in the loader contract | **met** | `e2e_scenario_schema.json` properties are only the nine §4 fields; root `additionalProperties: false`. No `cbc` / `CBC` / `AlertEnvelope` / `alert_envelope` in schema or fixture. Fresh probe: root `cbc: {}` and `alert_envelope: {}` → `unexpected fields`. |

## Gaps

None that fail Task 3 acceptance.

Residual (non-blocking, not Task 3 AC failures):

- Missing-`theater_detector` has no dedicated pytest. Prescribed suite tests unknown name, not omission. Behavior was confirmed by an independent loader probe this session; dropping the key from schema `required` would still leave the four tests green.
- `list_e2e_scenarios` is untested (glob/sort/default dir).
- `setup` is an unconstrained object; `setup.skip: true` loads (fresh probe ACCEPTED). Packet skip AC is the top-level flag, which is rejected.
- Custom validator matches the plan snippet: most JSON Schema types (`minLength`, non-object `arms`) are not turned into `ValueError`.
