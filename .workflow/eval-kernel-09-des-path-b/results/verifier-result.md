# Verifier result — eval-kernel-09-des-path-b (Task 9)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 9 is done — `des.path_b_stays_out_of_src` pins that `src/praetor` does not import `evals.capability.flatten` or a Path B flattener; both `old_build` and `new_build` pass on FakeProvider; a live Path B import under `src/praetor` is a `theater_detector` fail; Path B remains under `evals/`; no Path B import was added to `src/praetor/`.

Implementer results (`2 passed`, ruff/mypy green, `src/praetor/` untouched) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass | **met** | YAML pins both arms `provider: fake` with `path_b_import_found: false` (`evals/e2e_scenarios/des.path_b_stays_out_of_src.yaml:9-16`). Fresh `test_des_path_b_stays_out_of_src.py` → 2 passed. Independent `run_e2e_kernel` dump: both arms `status=pass`, `failure_class=none`, `provider=fake`, `observed.path_b_import_found=False`. |
| src/praetor import of `evals.capability.flatten` or a Path B flattener is a theater_detector fail | **met** | `_run_des_path_b` calls `run_theater_detector("path_b_in_src", ...)` and pins `path_b_import_found` to `finding.tripped` (`evals/e2e_kernel.py:312-334`). YAML `theater_detector: path_b_in_src` re-runs the same detector in `run_e2e_scenario` (`:111-131`); a trip overwrites `failure_class` to `theater_detector`. Independent plant: `from evals.capability.flatten import flatten_event_to_fact` and `import evals.capability.bundle` both trip `_path_b_in_src`. `_PATH_B_MODULES` is those two names (`evals/theater.py:18,83-95`). Did not mutate `src/praetor/`; trip proven on a temp tree plus the wired overwrite. |
| Path B remains under evals/ | **met** | `evals/capability/flatten.py` and `evals/capability/bundle.py` still present. `src/` has zero `*flatten*` paths and zero paths containing `capability`. `rg` over `src/` for `evals.capability`, `flatten_event`, `SPIKE_UNKNOWN_SOURCE`, `PATH_B_MAX_FACTS`: no matches. `f9e918e` does not touch `src/`. |
| Verifier checks only Task 9 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No remaining-10 YAML required; no Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_des_path_b_stays_out_of_src.py -q` | **0** | `..` — 2 passed in 2.47s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_path_b_stays_out_of_src.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~2.5s) is consistent with real kernel load (gov + envelope YAMLs + missing-ID error rows; the test filters to this ID).

Product files match HEAD `f9e918e`:
- `evals/e2e_kernel.py` `92ba919f90e7cf987aa0aab09b56d755107e002b`
- `evals/e2e_scenarios/des.path_b_stays_out_of_src.yaml` `891524038d9050c95459ed03006c815082eec686`
- `tests/evals/e2e/test_des_path_b_stays_out_of_src.py` `7efd198f4fcdf966fba52155e3c538b8e0fb4fb6`

`git diff f9e918e^ f9e918e` names only those three files. `git diff HEAD -- src/praetor` empty.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| No `src/praetor/` Path B import added | **met** | `git diff f9e918e^ f9e918e -- src/` empty. `git diff HEAD -- src/praetor` empty. `rg` over `src/` for `evals.capability` / `from evals` / `import evals` / `flatten_event` / `PATH_B`: no matches. Live `path_b_in_src` walk of `C:\Users\oalan\Praetor\src\praetor` (132 `*.py` files; `src_root.exists()=True`) returned `tripped=False`. |
| Writes only allowed files | **met** | `f9e918e` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 10–19 YAML. |
| YAML / test match Task 9 snippet | **met** | `des.path_b_stays_out_of_src.yaml` and `test_des_path_b_stays_out_of_src.py` match plan Step 3 / Step 1. `_run_des_path_b` matches the approved snippet (including hardcoded `arm="old_build"`). Scorecard pin is the one named key. `theater_detector: path_b_in_src`. |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns `des.path_b_stays_out_of_src` with `runner=e2e_kernel`, realm `design`, pins exactly `path_b_import_found`, `theater_detector=path_b_in_src`, setup `src_root=src/praetor`.
- Fresh `run_e2e_kernel` dump: both arms pass; observed `path_b_import_found=False`, `theater_message=""`.
- `_run_des_path_b` on the live YAML document: `path_b_import_found=False`.
- `_run_des_path_b` with `setup.src_root` pointed at a temp tree containing `from evals.capability.flatten import flatten_event_to_fact`: `path_b_import_found=True` and a theater message naming the planted file.
- `run_e2e_scenario` on that planted document: `status=fail`, `failure_class=harness` (pin mismatch). Outer theater still scans hardcoded `Path("src/praetor")` (`evals/e2e_kernel.py:123`), which is clean, so it does **not** overwrite to `theater_detector`. On the wired YAML (`src_root=src/praetor`) both passes scan the same tree; a live import there would trip the pin **and** the outer detector, and the overwrite at `:128-131` would set `failure_class=theater_detector`.
- Missing `src_root`: `path_b_in_src` returns `tripped=False` (`evals/theater.py:84-85`). Confirmed with `Path("no_such_src_root_zzz")`. This session's clean result is not that branch: `src/praetor` exists and 132 files were walked.
- `from evals.capability import flatten` does **not** trip `_path_b_in_src` (module string is `evals.capability`, not in `_PATH_B_MODULES`). Task 4 limitation; prescribed detector.
- Kernel AST walk of `evals/e2e_kernel.py`: no `Import`/`ImportFrom` mentioning `capability` or `flatten`; no `importlib` / `__import__` text. `test_kernel_module_does_not_import_flatten` is `ImportFrom`-only (plan snippet).
- Dispatch is ID-gated (`evals/e2e_kernel.py:99-100`); does not also require `realm == design`. YAML realm is `design`. Inconsistency only.

## Gaps

None that fail Task 9 acceptance.

Residual (non-blocking, not Task 9 AC failures):

- Relative `src_root` + missing-dir-is-clean (`evals/e2e_kernel.py:315`, `evals/theater.py:84-85`). Interfaces text says `REPO_ROOT / "src" / "praetor"`; the Step 3 snippet uses `Path(str(setup["src_root"]))`. Wrong CWD keeps the pin green without walking. Plan-faithful. This session walked a real 132-file tree.
- Kernel AST test is `ImportFrom`-only. `import evals.capability.flatten` and `from evals.capability import flatten` are not asserted. Theater `_PATH_B_MODULES` is likewise two absolute module strings. Prescribed. Inspection of this kernel file is clean.
- Happy-path E2E does not inject a trip. Prescribed test only asserts current `src/praetor` is clean. Trip coverage lives in `tests/evals/test_theater.py` plus the independent plant above.
- `_run_des_path_b` ignores `arm`; both arms execute the same scan. Prescribed: identical expected pins on both arms; snippet hardcodes `arm="old_build"`.
- Queue item `eval-kernel-09-des-path-b` remains `in_progress` (implementer packet: do not mark done).
