# Code review — eval-kernel-01-scorecard (Task 1)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 1 only (scorecard schema + Pydantic model). Sprint 1 gate gaps ignored.
**Diff reviewed:** commit `204c0d4` (`evals/schemas/scorecard_schema.json`, `evals/scorecard.py`, `tests/evals/test_scorecard.py`) plus current disk contents of those three files. Uncommitted tree also has `.workflow/autopilot-queue.json` and `.workflow/eval-kernel-01-scorecard/` orchestration files; those are out of product scope and were not treated as Task 1 defects.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 1
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §4 scorecard table
- `.workflow/eval-kernel-01-scorecard/packets/code-reviewer.md`

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Spec §4 fields + enums | Present in JSON Schema and `ScorecardRow` |
| `additionalProperties: false` / `extra="forbid"` | Present |
| `pending` only for capability quality `new_build` | Implemented in `validate_scorecard_row` via `CAPABILITY_QUALITY_IDS` × `arm == "new_build"` |
| `failure_class` `none` on pass/pending; required non-`none` on fail/error | Implemented |
| Writes only allowed files | `204c0d4` touches only the three Task 1 files; no `src/praetor/**` or `evals/harness.py` edits |
| Extra product scope | None (no kernel, scenarios, CI, envelope/CBC) |
| Verification (this review) | `pytest tests/evals/test_scorecard.py -q` → 6 passed; `ruff check` clean; `mypy evals/scorecard.py` clean |

Implementation matches the approved Task 1 snippet verbatim (minus ruff import-order in the test file). Disk files match `204c0d4`.

## Non-blocking notes

1. **Honesty rules are not on `ScorecardRow` itself** (`evals/scorecard.py:39-57`). `ScorecardRow.model_validate()` accepts illegal `pending` and illegal `failure_class` combinations; only `validate_scorecard_row()` rejects them. This matches the plan, but later kernel/harness code must call the validator or the honesty contract is bypassed.

2. **JSON Schema does not encode cross-field honesty rules** (`evals/schemas/scorecard_schema.json`). Shape/`additionalProperties` only. A jsonschema-only consumer could emit `pending` for any ID. Same plan split: Pydantic validator owns honesty.

3. **Test holes vs the acceptance wording** (`tests/evals/test_scorecard.py`). The six plan tests can stay green if someone regresses these branches:
   - `cap.baseline_bag_path_a` / `cap.stump_parity_guard` + `old_build` + `pending` is never rejected.
   - `cap.stump_parity_guard` is only checked for set membership, not actually validated as a legal pending row.
   - `status="pending"` + `failure_class != "none"` is never asserted (`test_failure_class_none_when_pass_or_pending` only uses `pass` + `model`).
   - `status="error"` + `failure_class="none"` is never asserted (`test_failure_class_required_when_fail_or_error` only rejects `fail`+`none`).

4. **`scenario_id` tightness mismatch:** schema `minLength: 1` vs Pydantic `scenario_id: str` (empty string validates). Plan-faithful; not a Task 1 blocker.

5. **`realm` is not cross-checked on pending.** A quality ID with `realm="governance"` + `new_build` + `pending` is accepted. IDs are the plan’s gate; worth tightening when the kernel binds realm to ID.
