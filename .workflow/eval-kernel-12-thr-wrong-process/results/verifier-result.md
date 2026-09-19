# Verifier result — eval-kernel-12-thr-wrong-process (Task 12)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 12 is done — `thr.valid_cite_wrong_process` records that citations resolve to the parent Path A process while omitting the subject child process; both `old_build` and `new_build` pass the Sprint 1 authority pin (`authority_treats_valid_cite_as_right_subject: false`); cite-to-subject McNemar / Sprint 2 primary scoring is not implemented.

Implementer results (`1 passed`, ruff/mypy green, commit `088477a`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass the Sprint 1 authority pin | **met** | YAML pins both arms `authority_treats_valid_cite_as_right_subject: false` (`evals/e2e_scenarios/thr.valid_cite_wrong_process.yaml:14-25`). Fresh kernel dump: 2 rows; both `status=pass`, `failure_class=none`, `provider=fake`, `realm=threat`. Observed pin is `false` on both arms. |
| Citations resolve but omit the subject Path A fact; that miss is recorded | **met** | Independent `correlate_telemetry` + `validate_evidence_citations` on the same fixtures: parent `{1111…}` → `ev-aa918ada8947756e20f3cae5c0d7722c` (`cmd.exe`); subject `{2222…}` → `ev-4d05e4c33897b3c24991af9aa6f37b93` (`powershell.exe`); IDs differ. Parent cite: `valid=True`, `cite_to_subject=False`. Kernel `cited_evidence_id` matches the independently computed parent ID. Flip-cite of the subject is valid and `cite_to_subject=True`. Invalid id `ev-does-not-exist` is `valid=False`. |
| No cite-to-subject McNemar or Sprint 2 primary scoring is implemented | **met** | `rg` over `evals/e2e_kernel.py`, the new YAML, and the new test finds no McNemar / scipy / statsmodels / binomtest. `e2e_kernel.py` does not import `evals.capability.score`. `cite_to_subject_primary_earned` stays hardcoded `False` on `TheaterContext` (`evals/e2e_kernel.py:133`, `:336`). No new-vs-old comparison on the cite-to-subject binary. |
| Verifier checks only Task 12 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_thr_valid_cite_wrong_process.py -q` | **0** | `.` — 1 passed in 2.46s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_valid_cite_wrong_process.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~2.5s) is consistent with real kernel load (prior YAMLs + missing-ID error rows; the test filters to this ID).

Product files match HEAD `088477a7e185338b30788c64a001e8375b7e890b` (`feat(evals): pin thr.valid_cite_wrong_process cite-to-subject miss`). `git show --name-only 088477a` names only:

- `evals/e2e_kernel.py`
- `evals/e2e_scenarios/thr.valid_cite_wrong_process.yaml`
- `tests/evals/e2e/test_thr_valid_cite_wrong_process.py`

`git status --short` and `git diff HEAD` on those three paths are empty. Working tree matches HEAD for the product paths.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Cite-to-subject remains Sprint 2 PRIMARY, not implemented here | **met** | Miss is recorded as a boolean pin only. No McNemar α, no paired new-vs-old primary, no `cite_to_subject_primary_earned=True`. Theater detector `unearned_demo_claim` still treats the primary as unearned (`evals/theater.py:67-69`). |
| Writes only allowed files | **met** | `088477a` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 13–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). |
| YAML / test / executor match Task 12 snippet | **met** | YAML and test match plan Step 3 / Step 1. Executor matches Step 3; unused `ModelJudgment` import omitted. `REPO_ROOT` imported from `evals.harness`. Scorecard pins are the three named keys. |
| Dispatch wired | **met** | `run_e2e_scenario` calls `_run_thr_wrong_process` for `thr.valid_cite_wrong_process` (`evals/e2e_kernel.py:107-108`). |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns exactly one `thr.valid_cite_wrong_process` document; realm `threat`; theater `gate_scored_as_judgment`; both arms `provider: fake`.
- Fresh `run_e2e_kernel` dump: 2 rows; both `pass` / `none` / `fake` / `threat`; `citations_valid=True`; `cite_to_subject=False`; `authority_treats_valid_cite_as_right_subject=False`; `subject_process_guid={22222222-2222-2222-2222-222222222222}`; `cited_evidence_id=ev-aa918ada8947756e20f3cae5c0d7722c`.
- Direct `_run_thr_wrong_process` returns the same observed dict as the scorecard rows.
- Independent reconstruction (not via the kernel helper): 3 correlated facts (parent Sysmon 1, 4624, child Sysmon 1). `assemble_process_relationships` has both GUIDs. Parent cite validates; subject evidence id is absent from cited refs.
- Flip probe: citing the child fact keeps `valid=True` and sets `cite_to_subject=True`. Negative probe: `ev-does-not-exist` is `valid=False`. The miss pin is not a constant `False`.
- `gate_scored_as_judgment` cannot trip here: it requires `scorecard_is_quality_pass` and `scored_layer=policy_gate` in `excerpt_blob` (`evals/theater.py:104-110`). This ID is not in `CAPABILITY_QUALITY_IDS`; `excerpt_blob=""`; `cite_to_subject_primary_earned=False`.
- `_run_thr_wrong_process` does not call `process_alert_intake`. That is the approved Task 12 snippet (record the miss only), not Sprint 2 scoring.
- Dispatch is ID-gated (`evals/e2e_kernel.py:107`); YAML realm is `threat`.

## Gaps

None that fail Task 12 acceptance.

Residual (non-blocking, not Task 12 AC failures):

- Happy-path test asserts the three pinned booleans plus the subject GUID. A hardcoded `{citations_valid: True, cite_to_subject: False, …}` would keep the test green. This session matched `cited_evidence_id` to the independently hashed parent fact and showed a subject-cite flip, so the pin is not being satisfied by a constant on this tree.
- `authority_treats_valid_cite_as_right_subject` is `validation.valid and cite_to_subject` (`evals/e2e_kernel.py:394-396`). With the other two pins it is determined. Prescribed Sprint 1 derivation, not a separate PolicyGate check.
- Both arms run the same executor with no arm parameter. Prescribed.
- Queue item `eval-kernel-12-thr-wrong-process` remains `in_progress` (implementer packet: do not mark done).
