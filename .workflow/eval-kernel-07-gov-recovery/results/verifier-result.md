# Verifier result — eval-kernel-07-gov-recovery (Task 7)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 7 is done — kernel executor seeds a non-terminal `STAMP_RESOLVED` `auto_contain` candidate and runs `run_engine_startup_recovery` / recovery resolver (not a PolicyGate-only shortcut); recovered final disposition is `escalate`, proposed stays `auto_contain`, no containment directive is emitted; both `old_build` and `new_build` pass on FakeProvider.

Implementer results (`1 passed`, ruff/mypy green, `used_run_engine_startup_recovery: True`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass on FakeProvider | **met** | YAML pins both arms `provider: fake` with identical expected escalate / proposed `auto_contain` / no directive (`evals/e2e_scenarios/gov.recovery_never_contains.yaml:10-21`). Fresh `test_recovery_never_contains_both_arms` passed. Independent kernel dump: both arms `status=pass`, `failure_class=none`, `provider=fake`. Scorecard `provider` is the YAML `fake` pin, not a live Vertex path. This pin does not instantiate `FakeProvider`; judgment is `skeleton_model_judgment(proposed=AUTO_CONTAIN)` as prescribed by the Task 7 snippet. |
| Recovery never emits `auto_contain` | **met** | `_run_gov_recovery` (`evals/e2e_kernel.py:248-305`) seeds allocate → `ACTIVE` → `PENDING_STAMP` → succeeded stamp with `AUTO_CONTAIN` candidate → `STAMP_RESOLVED` → `run_engine_startup_recovery`. Fresh scorecard observed both arms: `recovered_final_disposition=escalate`, `recovered_proposed_disposition=auto_contain`, `containment_directive_emitted=False`. Causal probe (same seed helpers): without recovery, `decision_edict` count is **0**; with `run_engine_startup_recovery`, count is **1**, `final=escalate`, `proposed=auto_contain`, `containment_directive=None`, `stamp_status=succeeded`. Resolver path is `recover_single_attempt` → `_recovery_disposition_for_stamp` (`src/praetor/engine/recovery.py:297-298`), which forces `AUTO_CONTAIN` → `ESCALATE` (`recovery.py:122-128`; also `skeleton_policy_result` at `edict.py:43-49`). `build_decision_edict` does not attach a `containment_directive` (`edict.py:102-123`). |
| Pin uses `run_engine_startup_recovery` / recovery resolver, not a PolicyGate-only shortcut | **met** | Call site is `run_engine_startup_recovery(store, stamp_backend=backend)` (`evals/e2e_kernel.py:289`). `evals/e2e_kernel.py` has no `evaluate_policy_gate` import or call. Intake is not used on this ID. Seed matches `tests/engine/test_recovery_policy_pinning.py` (`test_successful_stamp_recovery_downgrades_autocontain_candidate`). |
| Verifier checks only Task 7 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No remaining-13 YAML required; no Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_gov_recovery_never_contains.py -q` | **0** | `.` — 1 passed in 3.22s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_recovery_never_contains.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~3.2s) is consistent with real store + startup recovery (kernel also loads Task 5/6 gov YAMLs and emits missing-ID error rows; the test filters to this ID).

Product files: `git diff` empty for `evals/e2e_kernel.py`, `evals/e2e_scenarios/gov.recovery_never_contains.yaml`, `tests/evals/e2e/test_gov_recovery_never_contains.py`. HEAD is `6939520` (`feat(evals): pin gov.recovery_never_contains on startup recovery`; 3 files, +110). `src/praetor/`, `evals/harness.py`, `evals/scenarios/`, `evals/outcome_matrix.py` clean.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Startup recovery / resolver, not PolicyGate-only | **met** | No `evaluate_policy_gate` in `evals/e2e_kernel.py`. Pins come from the first ledger `decision_edict` after `run_engine_startup_recovery` returns (`evals/e2e_kernel.py:289-301`). Causal probe: stamp+`STAMP_RESOLVED` alone writes **0** edicts; recovery is what appends the escalate edict. |
| Writes only allowed files | **met** | `6939520` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 8–19 YAML. `evals/e2e_scenarios/` still has only the three landed gov YAMLs plus `.gitkeep`. |
| YAML / test match Task 7 snippet | **met** | `gov.recovery_never_contains.yaml` and `test_gov_recovery_never_contains.py` match plan Step 3 / Step 1. Scorecard pins are the three named keys. `theater_detector: stipulated_capability` stays clean (gov ID is not in `CAPABILITY_QUALITY_IDS`; notes empty). |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns `gov.recovery_never_contains` with `runner=e2e_kernel`, realm `governance`, pins exactly the three Task 7 keys, `theater_detector=stipulated_capability`, setup `seed=stamp_resolved_autocontain_candidate`.
- Fresh `run_e2e_kernel` dump: both arms pass; observed includes `used_run_engine_startup_recovery: True` and the three pins; notes empty (theater did not trip).
- Causal recovery probe (same seed as the executor):
  - stamp succeeded + `STAMP_RESOLVED`, **no** `run_engine_startup_recovery`: 0 `decision_edict` rows — observations are not a leftover activation/stamp edict.
  - same seed + `run_engine_startup_recovery`: 1 edict, `final=escalate`, `proposed=auto_contain`, `containment_directive=None`, `fault_flags=[]`, `stamp_status=succeeded`.
- Justified deviation vs pasted plan executor: function-local reimports of `fetch_active_snapshot` and `Disposition` omitted because both are already imported at module top (`evals/e2e_kernel.py:29-30`). Behavior matches the snippet.
- `_run_gov_recovery` ignores `arm`; both arms execute the same recovery seed. Prescribed: identical expected pins on both arms.
- Dispatch is ID-gated (`evals/e2e_kernel.py:95-96`); does not also require `realm == governance` (Task 5 dispatch does). YAML realm is `governance`. Inconsistency only.

## Gaps

None that fail Task 7 acceptance.

Residual (non-blocking, not Task 7 AC failures):

- `used_run_engine_startup_recovery` is hardcoded `True` after recovery returns (`evals/e2e_kernel.py:302`). Plan-faithful. Do not treat that key as independent proof; the ledger pins plus the causal probe are the proof.
- YAML `seed` is unused by the executor (`evals/e2e_scenarios/gov.recovery_never_contains.yaml:8`). `_run_gov_recovery` hardcodes the stamp-resolved autocontain seed and only reads `alert_identity`. Prescribed by the plan YAML + executor pair.
- `containment_directive_emitted` cannot fail on this persist path unless edict construction later starts attaching a directive. The `recovered_final_disposition=escalate` pin is what actually forbids emitting `auto_contain`.
- Queue item `eval-kernel-07-gov-recovery` remains `in_progress` (implementer packet: do not mark done).
