# Code review — eval-kernel-17-cap-baseline (Task 17)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 17 only (`cap.baseline_bag_path_a`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `f859046` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/cap.baseline_bag_path_a.yaml`, `tests/evals/e2e/test_cap_baseline_bag_path_a.py`). HEAD is `f859046`; working tree matches that commit for those three paths. No `src/praetor/**` edits. No Task 18 YAML.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 17 (through commit, before Task 18)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `cap.baseline_bag_path_a` and FakeProvider quality prohibition
- `.workflow/eval-kernel-17-cap-baseline/packets/code-reviewer.md`
- `.workflow/eval-kernel-17-cap-baseline/plan.md` acceptance and `files_allowed`
- `.workflow/autopilot-queue.json` item `eval-kernel-17-cap-baseline`

## Blocking findings

None.

## Confirmations (packet)

| Required pin | Result |
|---|---|
| `new_build` is `pending`, not `pass` | **Confirmed.** After pin match, `run_e2e_scenario` forces `CAPABILITY_QUALITY_IDS` + `arm == "new_build"` + `status != "fail"` to `status="pending"`, `failure_class="none"` (`evals/e2e_kernel.py:152-158`). This ID is in `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-17`). Test asserts `rows["new_build"].status == "pending"` and `failure_class == "none"` (`tests/evals/e2e/test_cap_baseline_bag_path_a.py:24-25`). `old_build` stays `pass` (bag-path pin, not quality). `validate_scorecard_row` accepts pending only for quality `new_build`. |
| Path A correlator bag | **Confirmed.** `_run_cap_baseline` calls `correlate_telemetry(sysmon_events=, security_events=, anchor_time=)` then `process_alert_intake(..., sysmon_events=, security_events=, anchor_time=)` (`evals/e2e_kernel.py:375-403`). Intake defaults `correlate=True` and re-runs `correlate_telemetry` in `_resolve_intake_evidence_bundle` (`orchestrator.py:121-130`). Fixtures are Sysmon EventID 1 (`tests/fixtures/sysmon/process_chain.json`) and Security 4624 (`tests/fixtures/security/successful_logon_4624.json`). Observed `path_a_event_ids == [1, 4624]`. No `evals.capability.flatten` / `bundle`. |
| No FakeProvider quality pass | **Confirmed.** `_quality_pass_forbidden` returns `False` for this ID even when bag-path status is `pass` (`evals/e2e_kernel.py:74-77`), so `stipulated_capability` stays clean (`evals/theater.py:58-64`). `proposed_disposition` / `frozen_label` are recorded in observed extras, not in `scorecard_pins`. YAML `theater_detector: stipulated_capability`. Frozen label `malicious` is not in `alert_identity` (`cap.baseline_bag_path_a`). |
| No Path B | **Confirmed by inspection.** `evals/e2e_kernel.py` has no `evals.capability.flatten` / `evals.capability.bundle` import. Executor does not call a Path B builder. Observed `used_path_b` is `False` (hardcoded in the prescribed snippet). Intake evidence path is production `correlate_telemetry`. |

## Checks

| Check | Result |
|---|---|
| YAML / test / executor match Task 17 snippet | YAML matches Step 3 text. Test matches Step 1 text. Executor matches Step 3 except the optional `event.get("EventID")` fallback (see Minor #3). Dispatch wired at `e2e_kernel.py:119-120`. Scorecard pins are the four named keys. Commit message matches Step 5. |
| `old_build` recorded as bag-path `pass` | Pins: `used_correlate_telemetry`, `used_process_alert_intake`, `used_path_b=false`, `path_a_event_ids=[1, 4624]`. Test asserts `old_build.status == "pass"`. Theater does not reclassify that pass as quality (special-case above). Without that special-case, `stipulated_capability` would trip on `status=pass` *before* the pending override and both arms would go `fail`. |
| Writes only allowed files | `f859046` is the three Task 17 product paths only. No spec/plan mutation, no `src/`, no Task 18 files. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None beyond the required `_quality_pass_forbidden` carve-out for this ID (Interfaces text: never set `scorecard_is_quality_pass=True` for this ID). |
| Verification (this review) | `pytest tests/evals/e2e/test_cap_baseline_bag_path_a.py tests/evals/test_scorecard.py -q` → 7 passed in 4.10s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Happy-path pin test would accept a stub** (`tests/evals/e2e/test_cap_baseline_bag_path_a.py:16-25`). Asserted keys are the four observed booleans/ids plus statuses. A hardcoded observed dict with `path_a_event_ids=[1, 4624]` and the three flags, plus the existing pending override, would stay green without calling `correlate_telemetry` or `process_alert_intake`. Prescribed Step 1. Track only.

2. **`used_path_b` is not measured** (`evals/e2e_kernel.py:412`). Always `False`. A later flatten import in this executor would not flip the pin. Plan-faithful. No-Path-B confirmation in this review is the import/call-site inspection, not that boolean.

3. **`event.get("EventID")` fallback omitted** (`evals/e2e_kernel.py:380-384` vs plan `:3002-3006`). Current fixtures expose top-level `EventID`; `event_field` returns it. Equivalent on the locked fixtures. Track only.

## Verdict rationale

Task 17 is the bag-path pin, not a capability-quality claim. `f859046` implements the approved YAML, executor, dispatch, and test. `new_build` is forced `pending`; `old_build` is bag-path `pass` without `scorecard_is_quality_pass=True`; the bag is production `correlate_telemetry` (Sysmon 1 + Security 4624) into `process_alert_intake`; FakeProvider stipulation is recorded, not scored; Path B is absent. No `files_allowed` breach. **approve**.
