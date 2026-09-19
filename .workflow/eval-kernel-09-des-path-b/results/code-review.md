# Code review — eval-kernel-09-des-path-b (Task 9)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 9 only (`des.path_b_stays_out_of_src`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `f9e918e` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/des.path_b_stays_out_of_src.yaml`, `tests/evals/e2e/test_des_path_b_stays_out_of_src.py`) plus current disk contents of those files. Working tree matches `f9e918e` for the product files. `src/praetor/**` has an empty diff vs parent. Path B remains under `evals/capability/` (`flatten.py`, `bundle.py`).

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 9 (through commit, before Task 10)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `des.path_b_stays_out_of_src`; §4 kernel must not import Path B; §8 `path_b_in_src`
- `.workflow/eval-kernel-09-des-path-b/packets/code-reviewer.md`
- `.workflow/eval-kernel-09-des-path-b/plan.md` acceptance
- Detector: `evals/theater.py` `_path_b_in_src` / `_PATH_B_MODULES` (`evals.capability.flatten`, `evals.capability.bundle`)

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| AST/import guard wired | `_run_des_path_b` calls `run_theater_detector("path_b_in_src", ...)` and pins `path_b_import_found` to `finding.tripped` (`evals/e2e_kernel.py:312-334`). Dispatch added for this ID (`:99-100`). YAML `theater_detector: path_b_in_src` also re-runs the same detector in `run_e2e_scenario` (`:111-131`). A live flatten/bundle import under `src/praetor` trips the detector (Task 4) and fails the row as `theater_detector`. |
| No Path B promotion | `f9e918e` touches only the three Task 9 product paths. Empty `git diff` vs parent on `src/praetor/**`. `evals/capability/flatten.py` and `bundle.py` stay under `evals/`. `rg` of `src/praetor` for `evals.capability` / flatten / bundle: no matches. |
| Kernel does not import flatten | `e2e_kernel.py` has no `flatten`, `capability.bundle`, `importlib`, or `__import__`. Top-level imports are harness/scorecard/praetor Path A. Lazy imports are `evals.theater`, envelope ValidationError, gov-recovery praetor modules, `evals.e2e_scenario`. `test_kernel_module_does_not_import_flatten` AST-walks `ImportFrom` against `evals.capability.flatten`. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with `path_b_import_found: false`. Test asserts `{old_build, new_build}`, `status=pass`, pin false, `failure_class=none`. Fresh run: 2 passed. |
| YAML / test / executor match Task 9 snippet | `des.path_b_stays_out_of_src.yaml` and both tests match plan Step 3 / Step 1 text. `_run_des_path_b` matches the approved snippet (including hardcoded `arm="old_build"` and `src_root=Path(str(scenario.setup["src_root"]))`). Scorecard pin is the one named key. |
| Writes only allowed files | `f9e918e` is the three Task 9 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 10–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_run_des_path_b` are the approved additive surface. |
| Verification (this review) | `pytest tests/evals/e2e/test_des_path_b_stays_out_of_src.py -q` → 2 passed in 2.39s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and theater call match the approved Task 9 snippet. Disk files match `f9e918e`. The pin leans on Task 4 `path_b_in_src`; this task does not re-implement the AST walker.

## Non-blocking notes

1. **Relative `src_root` + missing-dir-is-clean** (`evals/e2e_kernel.py:315`, `evals/theater.py:84-85`). Interfaces text says `REPO_ROOT / "src" / "praetor"`; the Step 3 snippet (and this commit) use `Path(str(setup["src_root"]))` → `src/praetor`. `_path_b_in_src` returns clean when `src_root` does not exist. Wrong CWD or a deleted tree keeps `path_b_import_found=false` and the outer theater pass clean. Plan-faithful. Pytest from repo root finds `src/praetor`. Do not treat a green pin as proof the walker ran.

2. **Kernel AST test is `ImportFrom`-only** (`tests/evals/e2e/test_des_path_b_stays_out_of_src.py:16-19`). `import evals.capability.flatten` (`ast.Import`) and `from evals.capability import flatten` (module `evals.capability`) are not asserted. Theater `_PATH_B_MODULES` is likewise two absolute module strings (Task 4). Prescribed. Inspection of this kernel file is clean.

3. **Happy-path E2E does not inject a trip.** The prescribed test only asserts current `src/praetor` is clean. A stubbed `_run_des_path_b` that always returns `false` would still fail the row if the outer `path_b_in_src` pass trips — and stay green if `src/praetor` is absent. Trip coverage lives in `tests/evals/test_theater.py`. Prescribed.

4. **Dispatch does not require `realm == design`** (`evals/e2e_kernel.py:99`). Same pattern as Tasks 6–8. YAML realm is `design`. Inconsistency only.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **CWD-relative `src_root` inherits Task 4 missing-dir-is-clean** (`evals/e2e_kernel.py:315`, `evals/theater.py:84-85`). Track only. Plan snippet over Interfaces `REPO_ROOT`. A later resolve against `EVALS_DIR.parent / setup["src_root"]` (or fail-closed when `src_root` is missing) would make the pin prove the walk ran.

2. **AST smuggle surface unchanged** (`tests/evals/e2e/test_des_path_b_stays_out_of_src.py:16-19`, `evals/theater.py:18,89-94`). Track only. Plan-faithful. `importlib` / `from evals.capability import flatten` stay outside this pin.
