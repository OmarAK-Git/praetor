# Code review — eval-kernel-05-gov-never-contain (Task 5)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 5 only (kernel executor + `gov.never_contain_live_shape`). Sprint 1 gate and remaining 14 IDs ignored.
**Diff reviewed:** commit `f9aca0e` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/gov.never_contain_live_shape.yaml`, `tests/evals/e2e/test_gov_never_contain_live_shape.py`, `tests/evals/e2e/__init__.py`) plus current disk contents of those files. Working tree matches `f9aca0e` for the product files. Uncommitted tree also has `.workflow/autopilot-queue.json` and `.workflow/eval-kernel-05-gov-never-contain/` orchestration files; those are out of product scope and were not treated as Task 5 defects.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 5 (through commit, before Task 6)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §4 / §5 `gov.never_contain_live_shape`
- `.workflow/eval-kernel-05-gov-never-contain/packets/code-reviewer.md`
- `.workflow/eval-kernel-05-gov-never-contain/plan.md` acceptance

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Production `process_alert_intake` (not PolicyGate-only) | `_run_gov_never_contain` calls `process_alert_intake(store, judgment_provider=..., stamp_backend=..., alert_identity=..., evidence_bundle=..., correlate=True)` (`evals/e2e_kernel.py:168-175`). No `evaluate_policy_gate` import or call in `e2e_kernel.py`. Gate evaluation happens only inside orchestrator intake (`src/praetor/engine/orchestrator.py:444`). Same helper stack as `evals/harness.py` `_run_engine_intake`: `_open_activated_store`, `_apply_emergency_never_contain_setup`, `_resolve_policy_bundle`, `_judgment_for_bundle`, `_CountingJudgmentProvider`, `_stamp_backend`, `_fetch_directive_for_decision_id`. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with identical expected escalate / `never_contain_live_conflict` / `directive_emitted: false`. `test_never_contain_both_arms_pass_via_intake` asserts `{old_build, new_build}`, `status=pass`, `provider=fake`. Fresh run: 7 passed. |
| YAML is Task 3 fixture verbatim | `evals/e2e_scenarios/gov.never_contain_live_shape.yaml` byte-matches `tests/evals/fixtures/e2e/gov.never_contain_live_shape.yaml`. `runner: e2e_kernel`. Setup is playbook call shape: `bundle: host`, `host_id: ws-01`, `proposed_disposition: auto_contain`, `emergency_never_contain`. |
| No CBC / envelope extras | Setup has no CBC JSON, no extra `AlertEnvelope` fields, no parallel eval envelope. Scorecard pins are `final_disposition` / `fault_flags` / `directive_emitted` only. |
| Other 14 IDs not added as real scenarios | `evals/e2e_scenarios/` contains only this YAML (+ `.gitkeep`). `run_e2e_kernel` still appends `scorecards_for_missing_ids` for the other 14 (`evals/e2e_kernel.py:245`). |
| Writes only allowed files | `f9aca0e` product files are the four allowed code/test/YAML paths plus `__init__.py`. No `src/praetor/**`, no OM scenario edits, no Task 6–19 YAML. |
| Extra product scope | None. Theater + `CAPABILITY_QUALITY_IDS` pending branch are in the approved Task 5 snippet, not later-task work. Sprint 1 gate not run. |
| Verification (this review) | `pytest tests/evals/e2e/test_gov_never_contain_live_shape.py tests/evals/test_e2e_kernel.py -q` → 7 passed; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

Implementation matches the approved Task 5 snippet. Justified deviation: `E2EScenarioDocument` / `list_e2e_scenarios` / theater imports are lazy (or `TYPE_CHECKING`) to avoid the `e2e_kernel` → `e2e_scenario` → `e2e_kernel` cycle flagged in the Task 3 review. Disk files match `f9aca0e`.

## Non-blocking notes

1. **`used_process_alert_intake` is self-attested** (`evals/e2e_kernel.py:185`). The executor hardcodes `True` after a successful intake return; the test asserts that key. A stubbed dict with the same four observed fields would keep `test_never_contain_both_arms_pass_via_intake` green. This is the plan snippet. The source path is the real pin — do not treat the flag as independent proof.

2. **YAML setup shape is untested** (`tests/evals/e2e/test_gov_never_contain_live_shape.py:10-14`). `test_never_contain_yaml_exists` only pins `runner` and `theater_detector`. Dropping `emergency_never_contain` / `proposed_disposition: auto_contain` from the YAML would still pass that test (the intake test would then fail for a different reason). Prescribed.

3. **Executor does not apply `_maybe_apply_explicit_containment_allow`** (`evals/e2e_kernel.py:161-162` vs `evals/harness.py:711-719`). OM `engine_intake` adds containment-allow when the proposal is `auto_contain`; the Task 5 snippet does not. Live never-contain still produces exactly `["never_contain_live_conflict"]` on this store, so the pin holds. Later gov scenarios that need allow-then-block should keep following their own plan snippets, not copy this omission by habit.

4. **Capability pending / theater scaffolding is unused by this ID** (`evals/e2e_kernel.py:66-67`, `118-124`). `gov.never_contain_live_shape` is not in `CAPABILITY_QUALITY_IDS`; `stipulated_capability` stays clean because `scorecard_is_quality_pass` is false. Required by the Task 5 executor frame; not evidence those later IDs work.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Self-attested intake flag** (`evals/e2e_kernel.py:185`, `tests/evals/e2e/test_gov_never_contain_live_shape.py:32`). Track only. Plan-faithful. A later static or monkeypatch test could assert `process_alert_intake` is the call site if this keeps getting cargo-culted.

2. **YAML contract test is thin** (`tests/evals/e2e/test_gov_never_contain_live_shape.py:10-14`). Track only. Setup pins live in the copied fixture; the intake test is what actually exercises them.
