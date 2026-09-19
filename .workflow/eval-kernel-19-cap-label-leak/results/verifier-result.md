# Verifier result — eval-kernel-19-cap-label-leak (Task 19)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 19 is done — `cap.no_label_leak_ids` both arms `pass` (not pending) when IDs do not leak; leak of GT labels / seed EventRecordID *labeling* / `expected_class` trips `failure_class=theater_detector`; all 15 required scenario IDs exist on disk.

Implementer results (`3 passed`, ruff/mypy green, both-arms-pass / 30-row claims) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass when IDs do not leak (no pending) | **met** | Live `run_e2e_kernel` this session: exactly 2 rows for `cap.no_label_leak_ids`; `old_build` and `new_build` both `status=pass`, `failure_class=none`, `label_leak_found=False`, `notes=""`, `provider=fake`. Dedicated test asserts the same (`tests/evals/e2e/test_cap_no_label_leak_ids.py:9-23`). ID is **not** in `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-17`; live `['cap.baseline_bag_path_a', 'cap.stump_parity_guard']`). Pending override cannot apply (`evals/e2e_kernel.py:158-164`). Independent `validate_scorecard_row` rejects this ID + `new_build` + `pending` (`ScorecardValidationError`: pending legal only for the two quality IDs). |
| Leak of labels, seed EventRecordIDs, or `expected_class` is `failure_class=theater_detector` | **met** | `theater_detector: label_leak` (`cap.no_label_leak_ids.yaml:25`). Needles `_LEAK_NEEDLES = ("expected_class", "EventRecordID", "ground-truth", "ground_truth")` (`evals/theater.py:13,50-55`). Live injection this session: mutated `alert_identity` containing `EventRecordID=1001` → row `fail` / `theater_detector` / `label_leak_found=True` / notes `EventRecordID visible in excerpts or alert_identity`. Same for `expected_class` in identity. Outer `run_e2e_scenario` remaps `theater.tripped` to `failure_class=theater_detector` (`evals/e2e_kernel.py:154-156`). Task 4 contract: needles trip when those **strings appear as GT labels** (`docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md:968`). |
| All 15 required scenario IDs now exist on disk | **met** | `evals/e2e_scenarios/` has 15 YAML files; stems == `REQUIRED_E2E_SCENARIO_IDS` (live). `list_e2e_scenarios` returns the same 15 IDs. `test_required_ids_are_the_locked_fifteen` passed. Live full suite: 30 rows, `kernel_exit_code==0`, ID set matches the locked fifteen. |
| Verifier checks only Task 19 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py::test_required_ids_are_the_locked_fifteen tests/evals/test_e2e_kernel.py::test_full_suite_has_thirty_rows_and_exits_zero -q` | **0** | `...` — 3 passed in 9.21s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_no_label_leak_ids.py tests/evals/test_e2e_kernel.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~9.2s) is consistent with real kernel load (the leak pin and the 30-row closure both call `run_e2e_kernel` against `evals/e2e_scenarios/`). Count is from the live `-q` run, not `--collect-only`.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Ground-truth stays harness-side | **met** | YAML keeps `expected_class: malicious` and `seed_event_record_id: "1001"` under `setup.hidden_ground_truth` (`cap.no_label_leak_ids.yaml:10-13`). Executor builds `excerpt_blob` from `correlate_telemetry` + `build_judgment_prompt_payload` on fixtures only (`evals/e2e_kernel.py:485-498`); `hidden` is read **after** payload construction solely for the `leaked` boolean (`:515-520`). Live excerpt has no `expected_class`, `malicious`, `EventRecordID`, `hidden_ground_truth`, or `ground_truth`. `alert_identity` is `cap.no_label_leak_ids` (no GT keys/values). |
| This ID is not forced pending | **met** | Not in `CAPABILITY_QUALITY_IDS`. Live both arms `pass`. Scorecard rejects pending on this ID (live + `tests/evals/test_scorecard.py:72-84`). Empty-directory harness-error test kept (`test_empty_directory_emits_harness_error_rows`); old `--e2e` exit-1-on-empty-tree test is gone; `test_harness_e2e_flag_exits_zero_after_full_suite` is the replacement (not in the required command set; noted only). |
| 15 YAML files exist under `evals/e2e_scenarios/` | **met** | 15 files; stems match the locked set including `cap.no_label_leak_ids.yaml`. Loader stem/id check would reject a mismatch (`evals/e2e_scenario.py:115-117`). |

## Independent probes (not in packet)

- Fresh `run_e2e_kernel` dump: 30 rows, exit 0. Quality `new_build` rows are the only `pending` (`cap.baseline_bag_path_a`, `cap.stump_parity_guard`). This ID: both arms `pass`/`none`.
- Live excerpt `1001` hits are telemetry provenance, not GT labeling: `source_event_reference=microsoft-windows-sysmon:1:1001` and SID `...-1001`. No `EventRecordID` string. Matches Task 4 needle contract and the prescribed test (`EventRecordID=1001` absent).
- Theater needles: `expected_class` / `EventRecordID` / `ground-truth` / `ground_truth` trip; bare `malicious` or `1001` do not.
- Injected kernel rows: GT-needle identity → `theater_detector`; value-only `…-1001` identity or `expected_class` value colliding with excerpt text (`WORKSTATION1`) → `fail`/`harness` with `label_leak_found=True` (pin fail without theater trip).
- Dispatch: `scenario_id == "cap.no_label_leak_ids"` → `_run_cap_no_label_leak_ids` (`evals/e2e_kernel.py:123-124`). YAML / test / executor match Task 19 Step 1 / Step 3 snippets (function renamed from `_run_cap_no_leak`).

## Gaps

None that fail Task 19 acceptance.

Residual (non-blocking, not Task 19 AC failures):

- Happy-path e2e does not inject a leak; it only asserts the clean path (`test_cap_no_label_leak_ids.py:9-23`, plan Step 1). Theater unit coverage is Task 4 (`test_theater.py:31-37`). This session proved the kernel remap with live mutated documents, so the missing e2e leak case is not the only proof.
- Value-only leaks (seed `1001` in `alert_identity` without the `EventRecordID` token, or `expected_class` *value* present in the excerpt without the key name) fail as `harness` via `label_leak_found`, not `theater_detector`. Plan-faithful: “Trip → theater_detector” is the needle detector. Spec table wording is broader; the extra `leaked` OR still fails the row.
- Seed value `1001` appears in provider excerpts as Path A `source_event_reference` (`…:1:1001`). That is fixture telemetry, not a GT label string. The prescribed test and Task 4 needles do not treat it as a leak. Executor checks `seed_event_record_id` only against `alert_identity` (`e2e_kernel.py:519`), matching the plan snippet.

Queue item status was not updated (implementer packet: do not mark done).
