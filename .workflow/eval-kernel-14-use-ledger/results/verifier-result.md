# Verifier result — eval-kernel-14-use-ledger (Task 14)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 14 is done — `use.reconstruct_from_ledger` pins that after completed intake, ledger rows plus `decision_id` / `evidence_bundle_hash` reconstruct the scorecard-asserted edict fields; both `old_build` and `new_build` pass; inability to rebuild the story is `failure_class=harness`.

Implementer results (`1 passed`, ruff/mypy green, commit `ffc09ec`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass | **met** | YAML pins both arms `provider: fake` with the three match keys `true` (`evals/e2e_scenarios/use.reconstruct_from_ledger.yaml:12-23`). Fresh `test_use_reconstruct_from_ledger.py` → 1 passed, 0 skipped. Independent `run_e2e_kernel` dump: 2 rows; both `status=pass`, `failure_class=none`, `provider=fake`, `realm=usability`; all three observed pins `True`. |
| Ledger reconstruction matches the scorecard-asserted edict fields | **met** | `_run_use_reconstruct` completes `process_alert_intake`, then rebuilds from `fetch_ledger_rows(store.conn)` (`evals/e2e_kernel.py:367-394`). Only `record_type == "decision_edict"` rows are validated as `DecisionEdict`. Latest row (`ORDER BY chain_sequence ASC`, then `[-1]`) is compared to `result.edict` on `decision_id`, `evidence_bundle_hash`, and `final_disposition`. Independent re-open of the same DB: ledger types `never_contain_snapshot` + `decision_edict`; one edict; 64-char `decision_id` and `evidence_bundle_hash`; `final_disposition=standard_review` (YAML proposed). Wrapped `fetch_ledger_rows`: 1 call, sequences 1 then 2. Wrapped intake: 1 call with production kwargs `alert_identity` / `evidence_bundle` / `judgment_provider` / `stamp_backend`. Field-level ledger mutations flip only the matching pin (`decision_id` / `evidence_bundle_hash` / `final_disposition`) to `False`. This is an independent ledger re-read, not an in-memory self-compare or hardcoded `True` dict. |
| Inability to rebuild the story is `failure_class=harness` | **met** | Empty `fetch_ledger_rows` → `status=error`, `failure_class=harness`, observed `RuntimeError` / `no decision_edict in ledger`. `result.edict is None` → `error` / `harness` (`AssertionError`). Pin mismatch (expected `ledger_decision_id_matches: false`) → `fail` / `harness`. Mutated ledger `decision_id` → `fail` / `harness` with `ledger_decision_id_matches=False`. Mutated hash → `fail` / `harness` with `ledger_evidence_bundle_hash_matches=False`. Mutated `final_disposition` → `fail` / `harness` with `ledger_final_disposition_matches=False`. Pin loop at `evals/e2e_kernel.py:117-120`; executor exceptions at `:165-172`. New code never assigns `model`. |
| Verifier checks only Task 14 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_use_reconstruct_from_ledger.py -q` | **0** | `.` — 1 passed in 3.27s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_use_reconstruct_from_ledger.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~3.3s) is consistent with real kernel load (prior YAMLs + missing-ID error rows; the test filters to this ID).

Product files match HEAD `ffc09ec2f7d07c3a12d364cf53e6ee6449f40e47` (`feat(evals): pin use.reconstruct_from_ledger from ledger rows`). `git show --name-only ffc09ec` names only:

- `evals/e2e_kernel.py`
- `evals/e2e_scenarios/use.reconstruct_from_ledger.yaml`
- `tests/evals/e2e/test_use_reconstruct_from_ledger.py`

`git status --short` and `git diff HEAD` on those three paths are empty. `git diff HEAD -- src/praetor` is empty. Working tree matches HEAD for the product paths.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Writes only allowed files | **met** | `ffc09ec` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 15–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Untracked tree is `.workflow/` queue leftovers plus this run dir. |
| YAML / test / executor match Task 14 snippet | **met** | YAML matches `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 14 Step 3. Test matches Step 1. `_run_use_reconstruct` matches Step 3 (`json` already imported at module top; no inner import). Dispatch wired at `evals/e2e_kernel.py:111-112`. Scorecard pins are the three named keys. |
| Dispatch wired | **met** | `run_e2e_scenario` calls `_run_use_reconstruct` for `use.reconstruct_from_ledger` (`evals/e2e_kernel.py:111-112`). |
| Stored edict is ledger-backed | **met** | `_append_edict_and_snapshot_in_transaction` returns `DecisionEdict.model_validate_json(result.record_json)` (`src/praetor/engine/edict.py:142-143`). `process_alert_intake` returns `IntakeResult.edict=stored` (`orchestrator.py:553-581`). Executor then re-reads via `fetch_ledger_rows`. |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns exactly one `use.reconstruct_from_ledger` document; realm `usability`; theater `stipulated_capability`; both arms `provider: fake`; pins are the three match keys.
- Fresh `run_e2e_kernel` dump: 2 rows; both `pass` / `none` / `fake` / `usability`; all three observed pins `True`; notes empty (theater did not trip).
- Live executor: `process_alert_intake` called once with `alert_identity=use.reconstruct_from_ledger` and a 2-fact host bundle. `fetch_ledger_rows` called once after intake.
- Independent DB re-open: `never_contain_snapshot` then `decision_edict`; reconstructed `final_disposition=standard_review`; both hashes 64 hex chars.
- Causal ledger mutations (patch `praetor.ledger.store.fetch_ledger_rows` after the inner import binds):
  - empty list → `error` / `harness` / `no decision_edict in ledger`
  - mutated `decision_id` → `fail` / `harness` / `ledger_decision_id_matches=False` (other pins stay `True`)
  - mutated `evidence_bundle_hash` → `fail` / `harness` / `ledger_evidence_bundle_hash_matches=False`
  - mutated `final_disposition` → `fail` / `harness` / `ledger_final_disposition_matches=False`
- Expected-pin flip (`ledger_decision_id_matches: false` while observed stays `True`) → `fail` / `harness`.
- `result.edict is None` after a real intake → `error` / `harness` (`AssertionError`).
- `stipulated_capability` cannot trip here: detector only fires on capability-quality `pass`; this ID is not in `CAPABILITY_QUALITY_IDS`.
- Dispatch is ID-gated (`evals/e2e_kernel.py:111`); YAML realm is `usability`.

## Gaps

None that fail Task 14 acceptance.

Residual (non-blocking, not Task 14 AC failures):

- Happy-path test would accept a stubbed `{ledger_*_matches: True}` dict (`tests/evals/e2e/test_use_reconstruct_from_ledger.py:18-21`). Prescribed. This session wrapped `fetch_ledger_rows` and flipped each pin by mutating ledger JSON, so do not treat the committed booleans as independent proof by themselves.
- No committed negative row that inability to rebuild is `failure_class=harness`. Classification is the existing kernel pin/exception loop. Track only; this session's empty-ledger and mutation probes are not part of the committed test.
- Last edict, not a `decision_id` / `evidence_bundle_hash` lookup (`evals/e2e_kernel.py:384`). Spec wording says those fields reconstruct the story; the plan compares them after taking `ledger_edicts[-1]`. Fresh DB + one intake makes `[-1]` the only edict. Plan-faithful.
- Both arms run the same executor with no arm parameter. Prescribed.
- Queue item `eval-kernel-14-use-ledger` remains `in_progress` (implementer packet: do not mark done).
