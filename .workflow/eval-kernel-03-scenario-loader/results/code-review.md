# Code review — eval-kernel-03-scenario-loader (Task 3)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 3 only (E2E scenario YAML contract loader). Sprint 1 gate gaps ignored. Scenario execution not in scope.
**Diff reviewed:** commit `9710405` (`evals/schemas/e2e_scenario_schema.json`, `evals/e2e_scenario.py`, `tests/evals/test_e2e_scenario.py`, `tests/evals/fixtures/e2e/gov.never_contain_live_shape.yaml`) plus current disk contents of those four files. Working tree matches `9710405` for the product files. Later `84c3033` is workflow-only (implementer result) and was not treated as a Task 3 defect.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 3
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §4 scenario contract
- `.workflow/eval-kernel-03-scenario-loader/packets/code-reviewer.md`
- `.workflow/eval-kernel-03-scenario-loader/plan.md` acceptance

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Sibling-tree placement | Fixture lives at `tests/evals/fixtures/e2e/`. `list_e2e_scenarios` defaults to `evals/e2e_scenarios` (Task 2 sibling dir). No YAML written under `evals/scenarios/`. |
| Stem / id match | `load_e2e_scenario` raises `ValueError` when `path.stem != scenario_id` (`evals/e2e_scenario.py:115-118`). Covered by `test_filename_stem_must_match_scenario_id`. |
| `theater_detector` required | Schema `required` includes `theater_detector`; enum matches the six §8 names. Runtime also rejects names outside `THEATER_DETECTOR_NAMES`. |
| No skip flags | Root `additionalProperties: false`. `skip: true` is rejected as `unexpected fields`. |
| Spec §4 required fields | `schema_version`, `scenario_id`, `realm`, `description`, `runner`, `setup`, `arms`, `scorecard_pins`, `theater_detector` are all required. `runner` const `e2e_kernel`. Arms require `old_build` / `new_build` with `expected` + `provider`. |
| OM schema untouched | `9710405` touches only the four Task 3 product files. `evals/schemas/scenario_schema.json` and `evals/scenarios/**` unchanged. |
| Writes only allowed files | No `src/praetor/**`. No Outcome Matrix loader edits. |
| Extra product scope | None (no executors, no `evals/e2e_scenarios/*.yaml` copies, no Sprint 1 gate). |
| Verification (this review) | `pytest tests/evals/test_e2e_scenario.py -q` → 4 passed; `ruff check` clean; `mypy evals/e2e_scenario.py` clean. |

Implementation matches the approved Task 3 snippet (line-wrap only on the theater-detector error string). Disk files match `9710405`.

## Non-blocking notes

1. **Missing `theater_detector` is untested** (`tests/evals/test_e2e_scenario.py`). Acceptance says the loader rejects a missing detector. Schema `required` does that today (`evals/schemas/e2e_scenario_schema.json:16`). The extra runtime check is `if theater and theater not in THEATER_DETECTOR_NAMES` (`evals/e2e_scenario.py:108`), so an empty/missing value is not rejected by that branch — only by schema `required` / enum. Dropping `theater_detector` from `required` would leave every current test green.

2. **`list_e2e_scenarios` is untested** (`evals/e2e_scenario.py:140-142`). The produced interface exists and defaults to `E2E_SCENARIOS_DIR`, but no test pins glob, sort, or the default directory. A broken glob would still pass Task 3.

3. **Custom validator does not enforce most JSON Schema types** (`evals/e2e_scenario.py:71-87`). `minLength`, non-object `arms` / `expected`, and non-mapping `$ref` targets are not turned into `ValueError`. `arms: []` can `AttributeError` on `.items()` after a clean error list (`evals/e2e_scenario.py:124`). This is the plan snippet, not a Task 3 deviation. Nested `$ref` + the second arm loop already cover the prescribed `expected`+`provider` shape for mapping arms.

4. **`evals.e2e_scenario` → `evals.e2e_kernel` import** (`evals/e2e_scenario.py:13`). Task 5’s plan adds the reverse import. If that import is placed above `E2E_SCENARIOS_DIR`, Python will raise `ImportError`. Plan-faithful; Task 5 must define the constant before importing this module (or move the path constant).

5. **Skip flags inside `setup` are not forbidden.** `setup` is `{ "type": "object" }` with no `additionalProperties: false`. A `setup.skip: true` document loads. The prescribed test only appends a top-level `skip`. Matches the plan; later YAML authors must keep skip keys off the document.

6. **`THEATER_DETECTOR_NAMES` and the schema enum are duplicated.** Drift is possible. `test_unknown_theater_detector_rejected` stays green if either layer still rejects `not_a_detector`.

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

- Missing-detector and `list_e2e_scenarios` coverage holes (`tests/evals/test_e2e_scenario.py`).
- Incomplete type checks / possible `AttributeError` on non-mapping `arms` (`evals/e2e_scenario.py:98-124`).
- Future circular import if Task 5 imports this module before `E2E_SCENARIOS_DIR` is bound (`evals/e2e_scenario.py:13`).

## Verdict rationale

Sibling-tree fixture, stem/id match, required `theater_detector`, skip-flag reject, and spec §4 field set are all present. Outcome Matrix schema and `evals/scenarios/**` were not touched. No Critical or Important defects. **approve** — ready for skeptic-verify.
