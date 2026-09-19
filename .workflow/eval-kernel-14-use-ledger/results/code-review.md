# Code review — eval-kernel-14-use-ledger (Task 14)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 14 only (`use.reconstruct_from_ledger`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `ffc09ec` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/use.reconstruct_from_ledger.yaml`, `tests/evals/e2e/test_use_reconstruct_from_ledger.py`) plus current disk contents of those files. HEAD is `ffc09ec`; working tree matches that commit for the three product paths. `src/praetor/**` has an empty diff vs parent.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 14 (through commit, before Task 15)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `use.reconstruct_from_ledger`
- `.workflow/eval-kernel-14-use-ledger/packets/code-reviewer.md`
- `.workflow/eval-kernel-14-use-ledger/plan.md` acceptance
- Production path: `process_alert_intake` → `_append_edict_and_snapshot_in_transaction` → `fetch_ledger_rows` → `DecisionEdict.model_validate(json.loads(row.record_json))`

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Ledger reconstruction of asserted edict fields | `_run_use_reconstruct` completes intake, then rebuilds from `fetch_ledger_rows(store.conn)` (`evals/e2e_kernel.py:377-394`). Only `record_type == "decision_edict"` rows are validated as `DecisionEdict`. Latest row (`ORDER BY chain_sequence ASC`, then `[-1]`) is compared to `result.edict` on `decision_id`, `evidence_bundle_hash`, and `final_disposition`. `IntakeResult.edict` is the stored edict (`orchestrator.py:553-581`, revalidated from `record_json` at append). This is an independent ledger re-read, not an in-memory self-compare. |
| Inability to rebuild is `failure_class=harness` | Empty ledger edict list raises `RuntimeError("no decision_edict in ledger")` (`e2e_kernel.py:382-383`). `result.edict is None`, `model_validate` failure, or any other executor exception becomes `status=error`, `failure_class=harness` (`:165-172`). Pin mismatch (`observed.get(pin) != expected.get(pin)`) becomes `status=fail`, `failure_class=harness` (`:117-120`). New code never assigns `model`. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with the three match keys `true`. Test asserts `{old_build, new_build}`, `status=pass`, and the three observed keys are `True`. Fresh run: 1 passed. |
| YAML / test / executor match Task 14 snippet | YAML matches Step 3 text. Test matches Step 1 text. Executor matches Step 3 text (`json` already imported at module top; no inner import). Dispatch wired at `e2e_kernel.py:111-112`. Scorecard pins are the three named keys. |
| Writes only allowed files | `ffc09ec` is the three Task 14 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 15–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_run_use_reconstruct` are the approved additive surface. |
| Verification (this review) | `pytest tests/evals/e2e/test_use_reconstruct_from_ledger.py -q` → 1 passed in 3.24s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and ledger re-read match the approved Task 14 snippet. Disk files match `ffc09ec`. Reconstruction uses the prescribed `fetch_ledger_rows` + `DecisionEdict.model_validate` surface, not a new lookup API.

## Non-blocking notes

1. **Happy-path test would accept a stubbed dict** (`tests/evals/e2e/test_use_reconstruct_from_ledger.py:18-21`). Asserted keys are only the three booleans. A hardcoded `{ledger_*_matches: True}` would keep the test green. Prescribed.

2. **No negative row that inability to rebuild is `failure_class=harness`.** Classification is the existing kernel pin/exception loop (`e2e_kernel.py:117-120`, `:165-172`), not new Task 14 logic. Track only; do not treat the passing test as proof of the mismatch path.

3. **Last edict, not a `decision_id` / `evidence_bundle_hash` lookup** (`evals/e2e_kernel.py:384`). Spec wording says those fields reconstruct the story; the plan compares them after taking `ledger_edicts[-1]`. Fresh DB + one intake makes `[-1]` the only edict. Plan-faithful.

4. **Dispatch does not require `realm == usability`** (`evals/e2e_kernel.py:111`). Same pattern as Tasks 6–13. YAML realm is `usability`. Inconsistency only.

5. **`stipulated_capability` cannot trip on this path.** Detector only fires on capability-quality `pass`. This ID is not in `CAPABILITY_QUALITY_IDS`; `run_e2e_scenario` also hardcodes `excerpt_blob=""` (`e2e_kernel.py:130`). Plan-faithful; the theater name is not independent proof.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Happy-path-only pin test** (`tests/evals/e2e/test_use_reconstruct_from_ledger.py:18-21`, `evals/e2e_kernel.py:385-393`). Track only. Plan-faithful. A later assert that `fetch_ledger_rows` was the source (or a negative row with `failure_class=harness`) would make rebuild-failure classification load-bearing.

2. **Last-row compare vs keyed reconstruct** (`evals/e2e_kernel.py:377-384`). Track only. Plan-faithful. The compared fields are the spec's reconstruct keys; they are not used as the fetch predicate.
