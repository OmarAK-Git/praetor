# Verifier result — eval-kernel-04-theater (Task 4)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 4 is done — theater detector registry with all six spec §8 names, a trip test and a clean test for each named check, and unknown detector names raising a harness error.

Implementer results (`done`, first-pass 6 tests, retry 14 tests, ruff/mypy green) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `THEATER_DETECTOR_NAMES` includes all six spec §8 names | **met** | Spec §8 names (`docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md:326-335`): `label_leak`, `stipulated_capability`, `unearned_demo_claim`, `path_b_in_src`, `post_hoc_protocol`, `gate_scored_as_judgment`. Same six live in `evals/e2e_scenario.py:16-25` and `DETECTORS` (`evals/theater.py:113-120`). Fresh probe: `set(DETECTORS) == set(THEATER_DETECTOR_NAMES)` is True. `test_detectors_match_theater_names` collected and passed. |
| Each named check has a unit test that trips and one that stays clean | **met** | Collect-only this session lists six dedicated trip tests plus six parametrized clean cases (`test_named_detector_stays_clean_on_default_ctx[<name>]`). Trip: `test_label_leak_trips_on_expected_class_in_excerpt`, `test_stipulated_capability_trips_on_quality_pass`, `test_unearned_demo_claim_trips_when_primary_unearned`, `test_path_b_in_src_trips_on_flatten_import`, `test_post_hoc_protocol_trips_on_relabel_marker`, `test_gate_scored_as_judgment_trips_on_quality_from_policy_gate` (`tests/evals/test_theater.py:31-108`). An always-trip registry would fail the clean parametrize; dropping `post_hoc_protocol` from `DETECTORS` would fail the name-pin and the `post_hoc` trip/clean cases. |
| Unknown detector names raise a harness error | **met** | `run_theater_detector` raises `KeyError("unknown theater detector: ...")` when the name is missing from `THEATER_DETECTOR_NAMES` or `DETECTORS` (`evals/theater.py:123-125`). `test_unknown_detector_raises` passed. Fresh probe: `not_a_detector` → `KeyError "unknown theater detector: 'not_a_detector'"`. No clean-finding fallback. |
| Verifier checks only Task 4 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set plus registry probes. No kernel executor, e2e YAML, CI, or sprint-exit suite was run. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/test_theater.py -q` | **0** | `..............` — 14 passed in 0.30s (no skips) |
| `ruff check evals/theater.py tests/evals/test_theater.py` | **0** | All checks passed |
| `mypy evals/theater.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

`pytest tests/evals/test_theater.py --collect-only -q` this session: 14 tests collected, the six trip tests + six clean parametrize cases + unknown-name + `DETECTORS`↔names pin. Tests import `evals.theater` from `C:\Users\oalan\Praetor\evals\theater.py`.

Product files: working-tree `git diff -- evals/theater.py tests/evals/test_theater.py` empty. Commits `dcd7e39` (implementation) and `04729ad` (trip+clean coverage). `04729ad` touches only `tests/evals/test_theater.py`. HEAD `04729addc736625447725089e83138a9c5e2a06f`.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| No silent skip path in the registry | **met** | Registry dispatch (`evals/theater.py:123-126`) either calls `DETECTORS[name](ctx)` or raises `KeyError`. There is no unknown-name `_clean`, no skip flag, and no `continue` that omits a named check. The only `continue` in the module (`evals/theater.py:73`) skips non-`.md/.html/.py/.txt` files inside `unearned_demo_claim` after that detector has already started. Tests have no `skip`/`xfail` markers. |

## Independent probes (not in packet)

- Module under test is this checkout’s `evals/theater.py`, not another install.
- Missing `src_root` for `path_b_in_src` returns `tripped=False` with an empty message (detector-internal “nothing to scan,” not a registry no-op). Default clean `path_b` actually walks existing `C:\Users\oalan\Praetor\src\praetor` and stays clean; `rg` over `src/` found no `evals.capability.flatten` / `evals.capability.bundle` imports.
- `label_leak` also trips when the needle is only in `alert_identity` (untested path, behavior confirmed).
- `unearned_demo_claim` stays clean when `cite_to_subject_primary_earned=True` even if `copy_roots` is the repo root.

## Gaps

None that fail Task 4 acceptance.

Residual (non-blocking, not Task 4 AC failures):

- `_path_b_in_src` reports clean when `src_root` does not exist (`evals/theater.py:84-85`). That is plan-snippet behavior. Task 5 must pass a real tree or a missing `src/` will look honest-green.
- Default clean for `unearned_demo_claim` uses empty `copy_roots`, so it does not prove “files scanned, no claim found.” The trip test does scan a real file.
- `stipulated_capability` trips on any `scorecard_is_quality_pass=True` and does not consult `CAPABILITY_QUALITY_IDS` / FakeProvider. Plan snippet is the same; Task 5 must set the boolean only for the illegal case.
- Several trip tests assert only `finding.tripped is True` (not `finding.detector`). Clean parametrize and two trip tests do pin the name.
