# Code review retry — eval-kernel-04-theater (Task 4)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context, scoped re-review)
**Scope:** Task 4 only (theater detector registry). Sprint 1 gate and Task 5 executor wiring ignored.
**Diff reviewed:** commit `04729ad` (`tests/evals/test_theater.py` only) against prior Task 4 commit `dcd7e39`. `evals/theater.py` is unchanged since `dcd7e39`. Working tree product files match `04729ad`. Uncommitted `.workflow/eval-kernel-04-theater/` orchestration files are out of product scope.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 4 (through commit, before Task 5)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §8 six named detectors
- `.workflow/eval-kernel-04-theater/plan.md` acceptance
- `.workflow/eval-kernel-04-theater/results/code-review.md` (prior blocking findings)
- `.workflow/eval-kernel-04-theater/packets/implementer-retry.md`

## Prior blocking findings — disposition

Prior review (`code-review.md`) verdict was `request_changes` for one Important finding: trip+clean coverage missing; `post_hoc_protocol` untested.

| Prior requirement | Status after `04729ad` |
|---|---|
| Trip test for `post_hoc_protocol` | **Addressed.** `test_post_hoc_protocol_trips_on_relabel_marker` (`tests/evals/test_theater.py:85-91`) calls `run_theater_detector("post_hoc_protocol", ...)` with `excerpt_blob="post_hoc_relabel after dispositions"` and asserts `tripped is True` and `detector == "post_hoc_protocol"`. |
| Clean test for each of the six §8 names | **Addressed.** `test_named_detector_stays_clean_on_default_ctx` (`:94-108`) parametrizes all six names and asserts `tripped is False` plus `detector == name`. Default `_ctx()` has no leak needles, `scorecard_is_quality_pass=False`, empty `copy_roots`, and no protocol/gate markers. |
| `DETECTORS` ↔ `THEATER_DETECTOR_NAMES` pin | **Addressed.** `test_detectors_match_theater_names` (`:111-115`). Dropping `_post_hoc_protocol` from `DETECTORS` now fails this pin plus the new trip/clean cases. |

Coverage after retry:

| Detector | Trip test | Clean test |
|---|---|---|
| `label_leak` | `test_label_leak_trips_on_expected_class_in_excerpt` | parametrized |
| `stipulated_capability` | `test_stipulated_capability_trips_on_quality_pass` | parametrized |
| `unearned_demo_claim` | `test_unearned_demo_claim_trips_when_primary_unearned` | parametrized |
| `path_b_in_src` | `test_path_b_in_src_trips_on_flatten_import` | parametrized |
| `post_hoc_protocol` | `test_post_hoc_protocol_trips_on_relabel_marker` | parametrized |
| `gate_scored_as_judgment` | `test_gate_scored_as_judgment_trips_on_quality_from_policy_gate` | parametrized |

An always-trip registry now fails the six clean cases. A missing `post_hoc_protocol` registration now fails the new trip, the matching clean case, and the name pin.

## Checks

| Check | Result |
|---|---|
| Six §8 names registered | Unchanged and still correct. `DETECTORS` keys match spec §8 and `THEATER_DETECTOR_NAMES` (`evals/theater.py:113-120`). Now pinned by `test_detectors_match_theater_names`. |
| Unknown name is a harness error | Unchanged. `run_theater_detector` raises `KeyError("unknown theater detector: ...")`. Covered by `test_unknown_detector_raises`. |
| Trip + clean unit test per named check | **Pass.** See table above. |
| Writes only allowed files | `04729ad` touches only `tests/evals/test_theater.py`. No `src/praetor/**`, no `evals/e2e_kernel.py`, no production YAML. `evals/theater.py` not modified. |
| Extra product scope | None. |
| Verification (this review) | `pytest tests/evals/test_theater.py -q` → 14 passed; `ruff check evals/theater.py tests/evals/test_theater.py` clean; `mypy evals/theater.py` clean. |

## Findings

### Critical

None.

### Important

None remaining. The prior Important finding is closed by `04729ad`.

### Minor (non-blocking; carried from prior review, unchanged implementation)

- **`stipulated_capability` still trusts a caller boolean** (`evals/theater.py:58-64`). Task 5 must set `scorecard_is_quality_pass` only for the illegal FakeProvider quality-pass case.
- **`path_b_in_src` still only matches two absolute module strings** (`evals/theater.py:18`, `:89-94`). Relative / `importlib` smuggles stay clean. Later smuggle tests should not assume this AST walk is complete.
- **Filesystem detectors still crash instead of returning a finding** (`evals/theater.py:71-74`, `:86-87`) on non-UTF8 or syntax-invalid files. The new clean parametrized case for `path_b_in_src` uses default `src_root=Path("src/praetor")`, which exists at repo root; that walk stayed clean in this review’s pytest run. Still out of Task 4 scope.
- **Four original trip tests still omit `finding.detector == name`.** The new `post_hoc_protocol` trip and all six clean cases do assert it. Not a retry regression.

## Verdict rationale

The retry stayed inside the allowed write set and added exactly the missing AC tests: a `post_hoc_protocol` trip, a clean path for each of the six §8 names, and a registry completeness pin. Implementation was already plan-faithful and was correctly left alone. Prior blocking finding is closed. Remaining items are the same non-blocking Task 5 / later-smuggle notes. **approve**.
