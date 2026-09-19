# Code review — eval-kernel-08-des-envelope (Task 8)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 8 only (`des.envelope_rejects_extra_fields`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `e74f3ad` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/des.envelope_rejects_extra_fields.yaml`, `tests/evals/e2e/test_des_envelope_rejects_extra_fields.py`) plus current disk contents of those files. Working tree matches `e74f3ad` for the product files. `src/praetor/contracts/alert.py` and `src/praetor/contracts/_base.py` have empty diffs vs parent `21eb3fc`.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 8 (through commit, before Task 9)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `des.envelope_rejects_extra_fields`
- `.workflow/eval-kernel-08-des-envelope/packets/code-reviewer.md`
- `.workflow/eval-kernel-08-des-envelope/plan.md` acceptance
- Contract: `AlertEnvelope` (`src/praetor/contracts/alert.py`) via `ContractModel` `extra="forbid"` (`src/praetor/contracts/_base.py:14-20`); JSON twin `schemas/alert_envelope.json` `additionalProperties: false`

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Extra envelope fields raise | `_run_des_envelope` calls `AlertEnvelope.model_validate` with `schema_version` + `alert_identity` + `setup["extra_field"]` (`cbc_edr_alert` → `{"id": "cbc-row-1"}`) (`evals/e2e_kernel.py:323-330`). `ContractModel` is `extra="forbid"` (`_base.py:14`). Extra keys raise `ValidationError`; executor sets `raises_validation_error=True`. |
| Identity-only construction succeeds | First `model_validate` uses only `schema_version` + `alert_identity` (`e2e_kernel.py:315-320`). Failure would propagate uncaught and fail the row. `accepted_legal_envelope` is `legal.alert_identity == setup["alert_identity"]`. |
| `src/praetor/contracts/alert.py` unchanged | Not in `e74f3ad`. Empty `git diff 21eb3fc e74f3ad -- src/praetor/contracts/alert.py src/praetor/contracts/_base.py`. No `src/praetor/**` writes. Envelope remains `schema_version` + `alert_identity` only (`alert.py:10-17`). |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with identical `raises_validation_error: true` / `accepted_legal_envelope: true`. Test asserts `{old_build, new_build}` and `status=pass`. Fresh run: 1 passed. |
| YAML / test match Task 8 snippet | `des.envelope_rejects_extra_fields.yaml` and `test_des_envelope_rejects_extra_fields.py` match the plan Step 3 / Step 1 text. Scorecard pins are the two named keys. `theater_detector: post_hoc_protocol` stays clean (`excerpt_blob=""`; detector only trips on protocol-mutation markers). |
| Writes only allowed files | `e74f3ad` touches only the three Task 8 product paths. No `src/praetor/**`, no OM scenario edits, no Task 9–19 YAML. `evals/e2e_scenarios/` now has the three landed gov YAMLs plus this design YAML plus `.gitkeep`. |
| Extra product scope | None. Dispatch branch + `_run_des_envelope` match the approved snippet. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Verification (this review) | `pytest tests/evals/e2e/test_des_envelope_rejects_extra_fields.py -q` → 1 passed; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and envelope calls match the approved Task 8 snippet. Disk files match `e74f3ad`. AG-0005 (`extra="forbid"` on contract models) is the enforcement the pin leans on; this task does not re-implement it.

## Non-blocking notes

1. **`except ValidationError` is unscoped** (`evals/e2e_kernel.py:331-332`). Any validation failure on the extra payload sets `raises_validation_error=True`. Adding `cbc_edr_alert` as a typed field that rejects a dict would keep the pin green (type error, not `extra=forbid`). Adding it as a dict-compatible field would fail the pin. This is the plan snippet. The source path is the real pin — do not treat a bare `ValidationError` as proof the rejected key was unknown.

2. **`rejected_cbc_field` is echoed from YAML** (`evals/e2e_kernel.py:321,337`). It is `str(setup["extra_field"])`, not an error-detail extract. The test asserts `== "cbc_edr_alert"`. A stubbed dict with the same three observed keys would keep the test green. Prescribed. `rejected_cbc_field` is not a scorecard pin.

3. **Dispatch does not require `realm == design`** (`evals/e2e_kernel.py:97`). `gov.never_contain_live_shape` checks both; this ID checks `scenario_id` only (same as Tasks 6–7). The YAML realm is `design`. Inconsistency only.

4. **`post_hoc_protocol` cannot trip on this path.** `run_e2e_scenario` hardcodes `excerpt_blob=""` (`evals/e2e_kernel.py:116`). `_post_hoc_protocol` only trips on markers in that blob. Plan-faithful; the theater name is not independent proof.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Unscoped `ValidationError` / echoed CBC field** (`evals/e2e_kernel.py:331-337`, `tests/evals/e2e/test_des_envelope_rejects_extra_fields.py:19-21`). Track only. Plan-faithful. A later check that the error loc is `cbc_edr_alert` (or that `extra=forbid` is still the model config) would close the typed-field hole.

2. **Unit-test overlap** (`tests/contracts/test_validators.py:197-201` already forbids a generic extra key on `AlertEnvelope`). This E2E ID is the locked design pin against CBC envelope expansion, not a new contract rule. Track only; do not delete either side.
