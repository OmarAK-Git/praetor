# Code review — eval-kernel-15-use-progressive-auth (Task 15)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 15 only (`use.progressive_auth_report`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `2f1df7c` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/use.progressive_auth_report.yaml`, `tests/evals/e2e/test_use_progressive_auth_report.py`) plus current disk contents of those files. HEAD is `2f1df7c`; working tree matches that commit for the three product paths. `src/praetor/**` has an empty diff vs parent.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 15 (through commit, before Task 16)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `use.progressive_auth_report`
- `.workflow/eval-kernel-15-use-progressive-auth/packets/code-reviewer.md`
- `.workflow/eval-kernel-15-use-progressive-auth/plan.md` acceptance
- Production path: `process_alert_intake` → `record_policy_gate_evaluation` (same edict `critical_transaction`) → `build_progressive_authorization_report(store.conn, window_start=, window_end=)`

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Report reads evaluation rows from the same intake | `_run_use_progressive` opens a fresh per-arm DB, completes `process_alert_intake`, then calls `build_progressive_authorization_report` on that same `store.conn` (`evals/e2e_kernel.py:413-432`). Intake writes `policy_gate_evaluations` via `record_policy_gate_evaluation` inside the edict `critical_transaction` (`orchestrator.py:509-571`). The report SELECTs those rows by `evaluated_at` window (`progressive_authorization.py:81-95`). Fresh store + one intake makes the window hit the just-written row. Independent re-read, not an in-memory self-compare. |
| Report is read-only | Production builder is SELECT-only (`progressive_authorization.py:67-77`). Pin is `report.read_only is True and PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY is True` (`e2e_kernel.py:443-447`). Constant is `True`; report dataclass defaults to it (`progressive_authorization.py:10,58`). |
| Missing evaluation row is `failure_class=harness` | Empty `policy_gate_by_dimension` yields `evaluation_row_present=False` (`e2e_kernel.py:434-436`). Pin mismatch becomes `status=fail`, `failure_class=harness` (`:119-122`). Executor exceptions become `status=error`, `failure_class=harness` (`:167-174`). New code never assigns `model`. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with the three keys `true`. Test asserts `{old_build, new_build}`, `status=pass`, and the three observed keys are `True`. Fresh run: 1 passed. |
| YAML / test / executor match Task 15 snippet | YAML matches Step 3 text. Test matches Step 1 text. Executor matches Step 3 text (inner `datetime` + reporting imports as prescribed). Dispatch wired at `e2e_kernel.py:113-114`. Scorecard pins are the three named keys. Commit message matches Step 5. |
| Writes only allowed files | `2f1df7c` is the three Task 15 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 16–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_run_use_progressive` are the approved additive surface. |
| Verification (this review) | `pytest tests/evals/e2e/test_use_progressive_auth_report.py -q` → 1 passed in 3.75s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and report re-read match the approved Task 15 snippet. Disk files match `2f1df7c`. The report uses the prescribed `build_progressive_authorization_report` surface on the same store connection after intake.

## Non-blocking notes

1. **Happy-path test would accept a stubbed dict** (`tests/evals/e2e/test_use_progressive_auth_report.py:18-21`). Asserted keys are only the three booleans. A hardcoded `{evaluation_row_present, report_read_only, override_rate_defined: True}` would keep the test green. Prescribed.

2. **No negative row that a missing evaluation row is `failure_class=harness`.** Classification is the existing kernel pin/exception loop (`e2e_kernel.py:119-122`, `:167-174`), not new Task 15 logic. Track only; do not treat the passing test as proof of the mismatch path.

3. **Same-intake is freshness + one write, not a `decision_id` join** (`evals/e2e_kernel.py:434-440`). Spec wording says the report reads rows written by the same intake; the plan checks `any(evaluations_total > 0)` / `any(override_rate is not None)` after one intake on a new DB. Fresh DB + one intake makes that the only row. Plan-faithful.

4. **`evaluation_row_present` and `override_rate_defined` are equivalent on this SQL.** `GROUP BY` only returns dimensions with `COUNT(*) > 0`, and `policy_gate_override_rate` is `None` iff `evaluations_total == 0` (`progressive_authorization.py:28-31`). Both pins are True iff the dimension tuple is non-empty. Prescribed.

5. **Read-only pin checks flags, not write-absence.** A future builder that writes but leaves `PROGRESSIVE_AUTHORIZATION_REPORT_READ_ONLY is True` would still pass. Production path is SELECT-only today. Plan-faithful.

6. **Hard-coded window expires 2026-12-31T00:00:00+00:00 exclusive** (`use.progressive_auth_report.yaml:11-12`). `evaluated_at` is `datetime.now(UTC)`. After that instant the happy path goes red. Plan-prescribed.

7. **Dispatch does not require `realm == usability`** (`evals/e2e_kernel.py:113`). Same pattern as Tasks 6–14. YAML realm is `usability`. Inconsistency only.

8. **`stipulated_capability` cannot trip on this path.** Detector only fires on capability-quality `pass`. This ID is not in `CAPABILITY_QUALITY_IDS`; `run_e2e_scenario` also hardcodes `excerpt_blob=""` (`e2e_kernel.py:132`). Plan-faithful; the theater name is not independent proof.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Happy-path-only pin test** (`tests/evals/e2e/test_use_progressive_auth_report.py:18-21`, `evals/e2e_kernel.py:434-448`). Track only. Plan-faithful. A later assert that the report row’s `decision_id` matches the intake, or a negative row with `failure_class=harness`, would make missing-row classification load-bearing.

2. **Window-bound happy path** (`evals/e2e_scenarios/use.progressive_auth_report.yaml:11-12`). Track only. Plan-faithful. After `2026-12-31T00:00:00+00:00` the same-intake row falls outside `evaluated_at < window_end`.
