# Verifier result — eval-kernel-05-gov-never-contain (Task 5)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 5 is done — kernel executor runs `gov.never_contain_live_shape` through production `process_alert_intake` (not a PolicyGate-only shortcut); `old_build` and `new_build` both pass on FakeProvider; no CBC JSON / extra AlertEnvelope fields; remaining 14 IDs not added as real scenarios; Outcome Matrix runners unchanged.

Implementer results (`7 passed`, ruff/mypy green, `used_process_alert_intake: True`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Scenario uses runner `e2e_kernel` and the production intake call shape | **met** | YAML `runner: e2e_kernel` (`evals/e2e_scenarios/gov.never_contain_live_shape.yaml:5`). SHA256 `84805A50F5B01662…7376` matches Task 3 fixture `tests/evals/fixtures/e2e/gov.never_contain_live_shape.yaml` byte-for-byte. Setup is the playbook `emergency_never_contain_intake.yaml` shape: `bundle: host`, `host_id: ws-01`, `proposed_disposition: auto_contain`, `emergency_never_contain`. Executor `_run_gov_never_contain` (`evals/e2e_kernel.py:168-175`) calls `process_alert_intake(store, judgment_provider=..., stamp_backend=..., alert_identity=..., evidence_bundle=..., correlate=True)` — same signature as `praetor.engine.orchestrator:255-271`. `test_never_contain_yaml_exists` asserts `doc.runner == "e2e_kernel"`. |
| `old_build` and `new_build` both pass on FakeProvider | **met** | YAML pins both arms `provider: fake` with identical expected escalate / `never_contain_live_conflict` / `directive_emitted: false`. Fresh `test_never_contain_both_arms_pass_via_intake` passed: both arms present, `status=pass`, `failure_class=none`, `provider=fake`. Judgment object is `_CountingJudgmentProvider` (`evals/e2e_kernel.py:165-167`) as prescribed by Task 5 snippet and as `evals/harness.py:737-739` does for bundle `engine_intake`. Scorecard `provider` is the YAML `fake` pin, not a live Vertex path. |
| `auto_contain` blocked by live never-contain on `process_alert_intake`, not a PolicyGate-only shortcut | **met** | `evals/e2e_kernel.py` has no `evaluate_policy_gate` import or call. Gate runs only inside production intake (`src/praetor/engine/orchestrator.py:444`). Live block is `read_live_never_contain_entries` + `_live_never_contain_blocks_authorization` → `_escalate(..., NEVER_CONTAIN_LIVE_CONFLICT)` (`src/praetor/policy/gate.py:377-379`). Setup applies live never-contain via `_apply_emergency_never_contain_setup` (`evals/e2e_kernel.py:162`). Fresh test asserts `final_disposition == "escalate"`, `"never_contain_live_conflict" in fault_flags`, `directive_emitted is False`. Those pins come from `result.edict` after a real intake return, not from a gate-only helper. |
| Verifier checks only Task 5 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No remaining-14 YAML required; no Sprint 1 / phase-exit suite run. `--e2e` still exits 1 (`test_harness_e2e_flag_exits_nonzero_on_empty_kernel` passed) because 14 IDs remain missing, which is expected until Task 19. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_gov_never_contain_live_shape.py tests/evals/test_e2e_kernel.py -q` | **0** | `.......` — 7 passed in 9.84s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_never_contain_live_shape.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~10s) is consistent with real store + intake, not a stubbed observed dict. Suite includes `test_empty_directory_emits_harness_error_rows` (still PASS) and `test_harness_default_still_runs_outcome_matrix_only` (OM default harness exit 0).

Product files: working-tree `git diff` vs `f9aca0e` empty for `evals/e2e_kernel.py`, `evals/e2e_scenarios/gov.never_contain_live_shape.yaml`, `tests/evals/e2e/test_gov_never_contain_live_shape.py`, `tests/evals/e2e/__init__.py`. Commit `f9aca0e` (`feat(evals): pin gov.never_contain_live_shape on process_alert_intake`). Queue item still `in_progress` (not marked done).

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| No CBC JSON or extra AlertEnvelope fields | **met** | Scenario setup keys are `alert_identity`, `bundle`, `host_id`, `proposed_disposition`, `emergency_never_contain` only. `rg` over `evals/e2e_kernel.py` and `evals/e2e_scenarios/` found no `cbc-`, `AlertEnvelope`, or extra-field construction. Scorecard pins are `final_disposition` / `fault_flags` / `directive_emitted` only. |
| Outcome Matrix runners unchanged | **met** | `git diff --name-only f9aca0e -- evals/outcome_matrix.py evals/harness.py evals/scenarios src/praetor` empty. Default OM harness still exits 0 (`test_harness_default_still_runs_outcome_matrix_only`). Playbook OM scenario `evals/scenarios/emergency_never_contain_intake.yaml` still `runner: engine_intake` (untouched). |
| Remaining 14 IDs not added as real scenarios | **met** | `evals/e2e_scenarios/` contains only `gov.never_contain_live_shape.yaml` + `.gitkeep`. `run_e2e_kernel` still appends `scorecards_for_missing_ids` for the other 14 (`evals/e2e_kernel.py:245`). |
| Writes only allowed files | **met** | `f9aca0e` product paths are the four allowed code/test/YAML files plus `__init__.py`. No `src/praetor/**`, no OM scenario edits, no Task 6–19 YAML. |

## Independent probes (not in packet)

- YAML is Task 3 fixture verbatim (identical SHA256).
- Executor dispatch is ID-gated: only `gov.never_contain_live_shape` runs; any other loaded YAML raises `LookupError` and becomes a scorecard `error` row (`evals/e2e_kernel.py:83-88`).
- `used_process_alert_intake` is self-attested (`evals/e2e_kernel.py:185`) after a successful intake return — same as the Task 5 plan snippet. A stubbed four-field dict would keep that one assertion green. The independent pins are edict disposition / live-conflict flag / no directive, which require the production intake + live never-contain path.
- `_run_gov_never_contain` ignores `arm`; both arms execute the same intake. Prescribed: identical expected pins on both arms.
- Executor omits harness `_maybe_apply_explicit_containment_allow`. Live never-contain still yields exactly `never_contain_live_conflict` on this store; the pin held under the fresh run.

## Gaps

None that fail Task 5 acceptance.

Residual (non-blocking, not Task 5 AC failures):

- `used_process_alert_intake` is hardcoded `True` after intake returns. Plan-faithful. Do not treat that key as independent proof; the edict pins are the proof.
- `test_never_contain_yaml_exists` only pins `runner` and `theater_detector`. Setup-shape coverage lives in the copied fixture plus the intake test, not that YAML contract test.
- Capability-pending / theater scaffolding in `run_e2e_scenario` is unused by this ID. Required by the Task 5 executor frame; not evidence later IDs work.
