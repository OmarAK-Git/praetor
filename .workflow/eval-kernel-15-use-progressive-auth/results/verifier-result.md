# Verifier result — eval-kernel-15-use-progressive-auth (Task 15)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 15 is done — `use.progressive_auth_report` pins that `build_progressive_authorization_report` reads evaluation rows written by the same intake, the report is read-only, both `old_build` and `new_build` pass, and a missing evaluation row is `failure_class=harness`.

Implementer results (`1 passed`, ruff/mypy green, commit `2f1df7c`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass | **met** | YAML pins both arms `provider: fake` with the three keys `true` (`evals/e2e_scenarios/use.progressive_auth_report.yaml:14-25`). Fresh `test_use_progressive_auth_report.py` → 1 passed, 0 skipped. Independent `run_e2e_kernel` dump: 2 rows; both `status=pass`, `failure_class=none`, `provider=fake`, `realm=usability`; all three observed pins `True`. Separate per-arm `run_e2e_scenario` calls both `pass`. |
| Report reads evaluation rows from the same intake and is read-only | **met** | `_run_use_progressive` completes `process_alert_intake`, then calls `build_progressive_authorization_report` on that same `store.conn` (`evals/e2e_kernel.py:416-432`). Wrapped intake: 1 call, `alert_identity=use.progressive_auth_report`. Wrapped report: 1 call after intake. At report time the table had one row whose `decision_id` matched the intake edict (`49abf72b…`); report dimension `unknown/unknown`, `evaluations_total=1`, `override_rate=0.0`. Production builder is SELECT-only (`progressive_authorization.py:67-95`). Pin is `report.read_only is True and PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY is True` (`e2e_kernel.py:443-447`). Patching the constant to `False` → `fail` / `harness` / `report_read_only=False`. Returning a report with `read_only=False` → same. This is an independent re-read, not an in-memory self-compare or hardcoded `True` dict. |
| A missing evaluation row is a harness fail | **met** | Empty `policy_gate_by_dimension` yields `evaluation_row_present=False` and `override_rate_defined=False` (`evals/e2e_kernel.py:434-440`). Pin mismatch becomes `status=fail`, `failure_class=harness` (`:119-122`). Executor exceptions become `status=error`, `failure_class=harness` (`:167-174`). New code never assigns `model`. DELETE of `policy_gate_evaluations` before the real report → `fail` / `harness` / both presence pins `False`. Empty report object → same. Window that excludes `evaluated_at` → same. Expected-pin flip (`evaluation_row_present: false` while observed stays `True`) → `fail` / `harness`. `result.edict is None` → `error` / `harness` (`AssertionError`). |
| Verifier checks only Task 15 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_use_progressive_auth_report.py -q` | **0** | `.` — 1 passed in 3.81s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_progressive_auth_report.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~3.8s) is consistent with real kernel load (prior YAMLs + missing-ID error rows; the test filters to this ID).

Product files match HEAD `2f1df7c70899e9f8fbc15071ebc336c089d01b7e` (`feat(evals): pin use.progressive_auth_report read-only report`). `git show --name-only 2f1df7c` names only:

- `evals/e2e_kernel.py`
- `evals/e2e_scenarios/use.progressive_auth_report.yaml`
- `tests/evals/e2e/test_use_progressive_auth_report.py`

`git status --short` and `git diff HEAD` on those three paths are empty. `git diff HEAD -- src/praetor` is empty. Working tree matches HEAD for the product paths.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Writes only allowed files | **met** | `2f1df7c` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 16–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Untracked tree is `.workflow/` queue leftovers plus this run dir. |
| YAML / test / executor match Task 15 snippet | **met** | YAML matches `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 15 Step 3. Test matches Step 1. `_run_use_progressive` matches Step 3 (inner `datetime` + reporting imports as prescribed). Dispatch wired at `evals/e2e_kernel.py:113-114`. Scorecard pins are the three named keys. |
| Dispatch wired | **met** | `run_e2e_scenario` calls `_run_use_progressive` for `use.progressive_auth_report` (`evals/e2e_kernel.py:113-114`). |
| Intake writes the row the report reads | **met** | `process_alert_intake` calls `record_policy_gate_evaluation` inside the edict `critical_transaction` (`orchestrator.py:509-571`). Report SELECTs `policy_gate_evaluations` by `evaluated_at` window (`progressive_authorization.py:81-95`). Fresh store + one intake makes that the only row. |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns exactly one `use.progressive_auth_report` document; realm `usability`; theater `stipulated_capability`; both arms `provider: fake`; pins are the three named keys.
- Fresh `run_e2e_kernel` dump: 2 rows; both `pass` / `none` / `fake` / `usability`; all three observed pins `True`; notes empty (theater did not trip).
- Live executor: `process_alert_intake` called once with `alert_identity=use.progressive_auth_report`. `build_progressive_authorization_report` called once after intake.
- Same-intake join: evaluation `decision_id` equals edict `decision_id`; dimension `unknown`/`unknown`; `evaluations_total=1`; `override_rate=0.0`; `evaluated_at` is `2026-09-19T04:41:46Z` (inside the YAML window).
- Causal missing-row probes (patch `praetor.reporting.progressive_authorization.build_progressive_authorization_report` so the inner import binds):
  - DELETE `policy_gate_evaluations` then real report → `fail` / `harness` / `evaluation_row_present=False`, `override_rate_defined=False`
  - empty `ProgressiveAuthorizationReport` → same
  - YAML window `2020-01-01`–`2020-02-01` → same
- Expected-pin flip (`evaluation_row_present: false` while observed stays `True`) → `fail` / `harness`.
- `result.edict is None` (patch `evals.e2e_kernel.process_alert_intake`) → `error` / `harness` (`AssertionError`).
- Read-only causality: module constant patched `False` → `fail` / `harness` / `report_read_only=False`. Report built with `read_only=False` → same. Presence pins stay `True`.
- `stipulated_capability` cannot trip here: detector only fires on capability-quality `pass`; this ID is not in `CAPABILITY_QUALITY_IDS`.
- Dispatch is ID-gated (`evals/e2e_kernel.py:113`); YAML realm is `usability`.

## Gaps

None that fail Task 15 acceptance.

Residual (non-blocking, not Task 15 AC failures):

- Happy-path test would accept a stubbed `{evaluation_row_present, report_read_only, override_rate_defined: True}` dict (`tests/evals/e2e/test_use_progressive_auth_report.py:18-21`). Prescribed. This session wrapped the real report and flipped each pin class (missing row / read-only / expected mismatch), so do not treat the committed booleans as independent proof by themselves.
- No committed negative row that a missing evaluation row is `failure_class=harness`. Classification is the existing kernel pin/exception loop. Track only; this session's DELETE / empty-report / window-miss probes are not part of the committed test.
- Same-intake is freshness + one write, not a `decision_id` join (`evals/e2e_kernel.py:434-440`). Spec wording says the report reads rows written by the same intake; the plan checks `any(evaluations_total > 0)` / `any(override_rate is not None)` after one intake on a new DB. Fresh DB + one intake makes that the only row. Plan-faithful.
- `evaluation_row_present` and `override_rate_defined` are equivalent on this SQL. `GROUP BY` only returns dimensions with `COUNT(*) > 0`, and `policy_gate_override_rate` is `None` iff `evaluations_total == 0`. Prescribed.
- Hard-coded window expires `2026-12-31T00:00:00+00:00` exclusive (`use.progressive_auth_report.yaml:11-12`). `evaluated_at` is `datetime.now(UTC)`. After that instant the happy path goes red. Plan-prescribed.
- Both arms run the same executor with no arm parameter. Prescribed.
- Queue item `eval-kernel-15-use-progressive-auth` remains `in_progress` (implementer packet: do not mark done).
