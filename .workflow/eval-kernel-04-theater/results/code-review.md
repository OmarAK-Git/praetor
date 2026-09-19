# Code review — eval-kernel-04-theater (Task 4)

**Verdict:** request_changes

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 4 only (theater detector registry). Sprint 1 gate and Task 5 executor wiring ignored.
**Diff reviewed:** commit `dcd7e39` (`evals/theater.py`, `tests/evals/test_theater.py`) plus current disk contents of those two files. Working tree matches `dcd7e39` for the product files. Uncommitted tree also has `.workflow/eval-kernel-04-theater/` orchestration files; those are out of product scope and were not treated as Task 4 defects.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 4 (through commit, before Task 5)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §8 six named detectors
- `.workflow/eval-kernel-04-theater/packets/code-reviewer.md`
- `.workflow/eval-kernel-04-theater/plan.md` acceptance

## Blocking findings

1. **Acceptance tests are missing.** Plan AC requires a trip test and a clean test for each of the six §8 names. The suite has five trip tests and no clean tests. `post_hoc_protocol` is untested. See Important #1.

## Checks

| Check | Result |
|---|---|
| Six §8 names registered | `DETECTORS` keys are `label_leak`, `stipulated_capability`, `unearned_demo_claim`, `path_b_in_src`, `post_hoc_protocol`, `gate_scored_as_judgment` (`evals/theater.py:113-120`). Matches spec §8 and `THEATER_DETECTOR_NAMES`. |
| Unknown name is a harness error | `run_theater_detector` raises `KeyError("unknown theater detector: ...")` (`evals/theater.py:123-125`). Covered by `test_unknown_detector_raises`. |
| Trip + clean unit test per named check | **Fail.** Trip tests exist for five names. No clean test for any name. No test at all for `post_hoc_protocol`. |
| `THEATER_DETECTOR_NAMES` completeness | The frozenset already lives in `evals/e2e_scenario.py:16-25` (Task 3). Task 4 correctly consumes it rather than redefining it. No Task 4 test pins `DETECTORS.keys() == THEATER_DETECTOR_NAMES`. |
| Writes only allowed files | `dcd7e39` touches only the two Task 4 product files. No `src/praetor/**`, no `evals/e2e_kernel.py`, no production YAML. |
| Extra product scope | None. `evals/e2e_kernel.py` does not import `run_theater_detector`. Sprint 1 gate not run. |
| Verification (this review) | `pytest tests/evals/test_theater.py -q` → 6 passed; `ruff check evals/theater.py tests/evals/test_theater.py` clean; `mypy evals/theater.py` clean. |

Implementation matches the approved Task 4 Step 3 snippet verbatim. Tests match the approved Step 1 snippet verbatim. Disk files match `dcd7e39`. The sprint snippet is a subset of the task AC — following it exactly still leaves the AC unmet.

## Findings

### Critical

None.

### Important

1. **Trip+clean coverage is missing; `post_hoc_protocol` is untested** (`tests/evals/test_theater.py:26-82`).

   Task plan AC: “Each named check has a unit test that trips and one that stays clean.” Current tests:

   | Detector | Trip test | Clean test |
   |---|---|---|
   | `label_leak` | yes (`:31`) | no |
   | `stipulated_capability` | yes (`:40`) | no |
   | `unearned_demo_claim` | yes (`:52`) | no |
   | `path_b_in_src` | yes (`:62`) | no |
   | `post_hoc_protocol` | **no** | no |
   | `gate_scored_as_judgment` | yes (`:73`) | no |

   Every existing detector test only asserts `finding.tripped is True`. A registry that always returns `_trip(...)` would keep all six tests green. Deleting `_post_hoc_protocol` from `DETECTORS` (`evals/theater.py:118`) would also stay green — nothing calls that name.

   **Fix:** keep the five plan trip tests. Add:

   ```python
   @pytest.mark.parametrize(
       "name",
       [
           "label_leak",
           "stipulated_capability",
           "unearned_demo_claim",
           "path_b_in_src",
           "post_hoc_protocol",
           "gate_scored_as_judgment",
       ],
   )
   def test_named_detector_stays_clean_on_default_ctx(name: str) -> None:
       finding = run_theater_detector(name, _ctx())
       assert finding.tripped is False
       assert finding.detector == name


   def test_post_hoc_protocol_trips_on_relabel_marker() -> None:
       finding = run_theater_detector(
           "post_hoc_protocol",
           _ctx(excerpt_blob="post_hoc_relabel after dispositions"),
       )
       assert finding.tripped is True
       assert finding.detector == "post_hoc_protocol"


   def test_detectors_match_theater_names() -> None:
       from evals.e2e_scenario import THEATER_DETECTOR_NAMES
       from evals.theater import DETECTORS

       assert set(DETECTORS) == set(THEATER_DETECTOR_NAMES)
   ```

   Default `_ctx()` is already a clean fixture (no leak needles, `scorecard_is_quality_pass=False`, empty `copy_roots`, non-existent `src/praetor` → `_path_b_in_src` returns clean). Do not treat the sprint Step 1 snippet as a ceiling; the task AC is stricter and is the gate the verifier will apply.

### Minor (non-blocking)

- **`stipulated_capability` trusts a caller boolean** (`evals/theater.py:58-64`). Spec §8 trips when FakeProvider `proposed_disposition` is scored as a capability quality `pass`. The detector does not consult `CAPABILITY_QUALITY_IDS`, realm, or provider. Plan snippet is the same; Interfaces listed those types as consumed and they are unused. Task 5 must set `scorecard_is_quality_pass` only for the illegal FakeProvider quality-pass case or this check will over-trip a real quality pass.

- **`path_b_in_src` only matches two absolute module strings** (`evals/theater.py:18`, `:89-94`). `from evals.capability import flatten` and `importlib.import_module("evals.capability.flatten")` stay clean. Spec wording is “imports a Path B flattener.” Plan-faithful; later smuggle tests should not assume this AST walk is complete.

- **Filesystem detectors crash instead of returning a finding** (`evals/theater.py:71-74`, `:86-87`). `read_text` / `ast.parse` raise on non-UTF8 or syntax-invalid files. Out of scope until `src_root` / `copy_roots` point at the real tree.

- **`scorecard_status`, `scenario_id`, `realm`, and `arm` are unused by every detector.** Harmless context for Task 5. Not a Task 4 defect.

## Verdict rationale

The six §8 detectors exist, unknown names raise `KeyError`, and `dcd7e39` stays inside the allowed write set. That is not enough. The task’s own acceptance requires a trip test and a clean test for each named check; those tests are not in `tests/evals/test_theater.py`. Without them the suite cannot detect an always-trip registry or a dropped `post_hoc_protocol`. **request_changes** — add the clean tests and a `post_hoc_protocol` trip (plus a `DETECTORS` ↔ `THEATER_DETECTOR_NAMES` pin) before skeptic-verify.
