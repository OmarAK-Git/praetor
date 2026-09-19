# Code review — eval-kernel-07-gov-recovery (Task 7)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 7 only (`gov.recovery_never_contains`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `6939520` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/gov.recovery_never_contains.yaml`, `tests/evals/e2e/test_gov_recovery_never_contains.py`) plus current disk contents of those files. Working tree matches `6939520` for the product files. Uncommitted tree also has `.workflow/autopilot-queue.json` and `.workflow/eval-kernel-07-gov-recovery/` orchestration files; those are out of product scope and were not treated as Task 7 defects.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 7 (through commit, before Task 8)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `gov.recovery_never_contains`
- `.workflow/eval-kernel-07-gov-recovery/packets/code-reviewer.md`
- `.workflow/eval-kernel-07-gov-recovery/plan.md` acceptance
- Seed pattern in `tests/engine/test_recovery_policy_pinning.py` (`test_successful_stamp_recovery_downgrades_autocontain_candidate`)
- Recovery resolver: `run_engine_startup_recovery` → `recover_single_attempt` → `_recovery_disposition_for_stamp` (`src/praetor/engine/recovery.py`)

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Recovery never emits `auto_contain` | `_run_gov_recovery` seeds a `STAMP_RESOLVED` attempt whose stamp payload proposes `AUTO_CONTAIN`, then calls `run_engine_startup_recovery`. Observed pins: `recovered_final_disposition=escalate`, `recovered_proposed_disposition=auto_contain`, `containment_directive_emitted=false`. Resolver path is `_recovery_disposition_for_stamp` (`recovery.py:297-298`), which forces `AUTO_CONTAIN` → `ESCALATE` (`recovery.py:122-128`) before `append_recovery_edict_for_attempt`. `build_decision_edict` does not attach a `containment_directive` (`edict.py:102-123`). |
| Uses `run_engine_startup_recovery` / recovery resolver, not PolicyGate-only | Call site is `run_engine_startup_recovery(store, stamp_backend=backend)` (`evals/e2e_kernel.py:289`). No `evaluate_policy_gate` import or call in `e2e_kernel.py`. Intake is not used on this ID. Seed matches the pinning test: allocate → `ACTIVE` → `PENDING_STAMP` → succeeded stamp with `AUTO_CONTAIN` candidate → `STAMP_RESOLVED` → recovery. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with identical expected escalate / proposed `auto_contain` / no directive. Test asserts `{old_build, new_build}` and `status=pass`. Fresh run: 1 passed. |
| YAML / test match Task 7 snippet | `gov.recovery_never_contains.yaml` and `test_gov_recovery_never_contains.py` match the plan Step 3 / Step 1 text. Scorecard pins are the three named keys. `theater_detector: stipulated_capability` stays clean (gov ID is not in `CAPABILITY_QUALITY_IDS`). |
| Writes only allowed files | `6939520` touches only the three Task 7 product paths. No `src/praetor/**`, no OM scenario edits, no Task 8–19 YAML. `evals/e2e_scenarios/` still has only the three landed gov YAMLs plus `.gitkeep`. |
| Extra product scope | None. Justified deviation: function-local reimports of `fetch_active_snapshot` and `Disposition` omitted because both are already imported at module top (`evals/e2e_kernel.py:29-30`). Behavior matches the snippet. Sprint 1 gate not run. |
| Verification (this review) | `pytest tests/evals/e2e/test_gov_recovery_never_contains.py -q` → 1 passed; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and recovery seed match the approved Task 7 snippet. Disk files match `6939520`.

## Non-blocking notes

1. **`used_run_engine_startup_recovery` is self-attested** (`evals/e2e_kernel.py:302`). The executor hardcodes `True` after the recovery return; the test asserts that key. A stubbed dict with the same four observed fields would keep the test green. This is the plan snippet. The source path is the real pin — do not treat the flag as independent proof. The disposition / directive pins still require a real ledger edict.

2. **YAML `seed` is unused by the executor** (`evals/e2e_scenarios/gov.recovery_never_contains.yaml:8`). `_run_gov_recovery` hardcodes the stamp-resolved autocontain seed and only reads `alert_identity`. Changing `seed` would not fail the test. Prescribed by the plan YAML + executor pair.

3. **`containment_directive_emitted` is weaker than the disposition pin on this path.** Recovery persist never writes an outstanding directive (`persist_edict_and_complete_attempt` appends snapshot + edict only). `build_decision_edict` leaves `containment_directive` as `None`. The directive pin therefore cannot fail unless edict construction later starts attaching one. The `recovered_final_disposition=escalate` pin is what actually forbids emitting `auto_contain`. Plan-faithful.

4. **Dispatch does not require `realm == governance`** (`evals/e2e_kernel.py:95`). `gov.never_contain_live_shape` checks both; this ID checks `scenario_id` only (same as Task 6). The YAML realm is `governance`. Inconsistency only.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Self-attested recovery flag** (`evals/e2e_kernel.py:302`, `tests/evals/e2e/test_gov_recovery_never_contains.py:22`). Track only. Plan-faithful. Same cargo-cult risk as Tasks 5–6.

2. **Unused YAML `seed`** (`evals/e2e_scenarios/gov.recovery_never_contains.yaml:8`). Track only. Plan-faithful. A later static pin on `setup["seed"]` would stop the hardcoded seed and the YAML from drifting apart.
