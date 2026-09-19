# Verifier result — eval-kernel-13-thr-multi-host (Task 13)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 13 is done — `thr.ambiguous_multi_host_target` pins that two distinct cited hosts produce `escalate` + `ambiguous_containment_target` on the production `process_alert_intake` call shape; both `old_build` and `new_build` pass.

Implementer results (`1 passed`, ruff/mypy green, commit `919897b`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass | **met** | YAML pins both arms `provider: fake` with `final_disposition: escalate` and `fault_flags: [ambiguous_containment_target]` (`evals/e2e_scenarios/thr.ambiguous_multi_host_target.yaml:17-28`). Fresh `test_thr_ambiguous_multi_host_target.py` → 1 passed, 0 skipped. Independent `run_e2e_kernel` dump: 2 rows; both `status=pass`, `failure_class=none`, `provider=fake`, `realm=threat`. |
| Two distinct cited hosts produce `ambiguous_containment_target` escalate | **met** | Fixture facts are `host-a-1`/`WORKSTATION1` and `host-b-1`/`WORKSTATION2` (`tests/fixtures/synthetic/multi_host_two_cited_hosts.json`). YAML cites both on `host_id` (`thr.ambiguous_multi_host_target.yaml:11-15`), matching playbook pin `evals/scenarios/multi_host_target_ambiguity.yaml:10-14`. `resolve_containment_target` on both IDs: `ambiguous=True`, `target=None`. One-ID control: `ambiguous=False`, target `host/WORKSTATION1`. Independent `process_alert_intake` with the same two refs: `escalate` + `['ambiguous_containment_target']` + `system_fault_escalation=False` + proposed `auto_contain`. One-cite control on the same bundle/path: `escalate` + `['insufficient_corroboration']`. The flag is caused by two distinct cited hosts, not a constant escalate stub. |
| Uses production `process_alert_intake` call shape | **met** | Executor calls `process_alert_intake(store, judgment_provider=..., stamp_backend=..., alert_identity=..., evidence_bundle=bundle)` (`evals/e2e_kernel.py:374-380`). That matches production kwargs (`src/praetor/engine/orchestrator.py:255-271`). Monkeypatch of the imported symbol: 1 call; keys `alert_identity`, `evidence_bundle`, `judgment_provider`, `stamp_backend`; alert `thr.ambiguous_multi_host_target`; bundle facts `host-a-1/WORKSTATION1` and `host-b-1/WORKSTATION2`. Intake keeps a provided bundle (`orchestrator.py:119-120`) and evaluates the gate internally (`orchestrator.py:444-451`). No `evaluate_policy_gate` import or direct call in `e2e_kernel.py`. |
| Verifier checks only Task 13 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_thr_ambiguous_multi_host_target.py -q` | **0** | `.` — 1 passed in 2.84s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_thr_ambiguous_multi_host_target.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~2.8s) is consistent with real kernel load (prior YAMLs + missing-ID error rows; the test filters to this ID).

Product files match HEAD `919897beea5f835af798f75d0c19794efbb69bcb` (`feat(evals): pin thr.ambiguous_multi_host_target on intake`). `git show --name-only 919897b` names only:

- `evals/e2e_kernel.py`
- `evals/e2e_scenarios/thr.ambiguous_multi_host_target.yaml`
- `tests/evals/e2e/test_thr_ambiguous_multi_host_target.py`

`git status --short` and `git diff HEAD` on those three paths are empty. Working tree matches HEAD for the product paths.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Writes only allowed files | **met** | `919897b` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 14–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Untracked tree is `.workflow/eval-kernel-13-thr-multi-host/` only. |
| YAML / test / executor match Task 13 snippet | **met** | YAML, test, and `_run_thr_multi_host` match `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 13 Steps 1 and 3. Scorecard pins are the two named keys; `used_process_alert_intake` stays observed-only. Citation refs `host-a-1` / `host-b-1` on `host_id`. |
| Dispatch wired | **met** | `run_e2e_scenario` calls `_run_thr_multi_host` for `thr.ambiguous_multi_host_target` (`evals/e2e_kernel.py:109-110`). |
| Same degraded/playbook fixture contract | **met** | Playbook `multi_host_target_ambiguity.yaml` uses the same fixture, citation refs, `auto_contain` proposal, and expected escalate + `ambiguous_containment_target`. E2E uses `process_alert_intake` instead of playbook `evaluate_policy_gate` — that is the Task 13 interface. |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns exactly one `thr.ambiguous_multi_host_target` document; realm `threat`; theater `stipulated_capability`; both arms `provider: fake`.
- Fresh `run_e2e_kernel` dump: 2 rows; both `pass` / `none` / `fake` / `threat`; `final_disposition=escalate`; `fault_flags=['ambiguous_containment_target']`; `used_process_alert_intake=True`; notes empty (theater did not trip).
- Monkeypatched `process_alert_intake` (the name `evals.e2e_kernel` imported): one live call with `evidence_bundle=` carrying both distinct hosts. Not a skipped / PolicyGate-only shortcut.
- Direct resolver: two cited IDs → `ambiguous=True`; one cited ID → host `WORKSTATION1`.
- Causal intake on the production function (same store helper, same bundle): two cites → `ambiguous_containment_target`; one cite → `insufficient_corroboration`. The two-host flag is not a constant on this tree.
- Gate order: citations validate, then `AUTO_CONTAIN` resolves the target, then `target_resolution.ambiguous` escalates `AMBIGUOUS_CONTAINMENT_TARGET` with `system_fault=False` (`src/praetor/policy/gate.py:336-353`; `containment_policy.py:134-135`). Independent edict `sfe=False` matches.
- `stipulated_capability` cannot trip here: detector only fires on capability-quality `pass` (`evals/theater.py:58-64`); this ID is not in `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-16`).
- Dispatch is ID-gated (`evals/e2e_kernel.py:109`); YAML realm is `threat`.

## Gaps

None that fail Task 13 acceptance.

Residual (non-blocking, not Task 13 AC failures):

- `used_process_alert_intake` is self-attested (`evals/e2e_kernel.py:385`). The executor hardcodes `True` after a successful intake return; the test asserts that key. A stubbed dict with the same three observed fields would keep the test green. This is the plan snippet. This session wrapped the real import and matched edict pins plus the one-host flag flip, so do not treat the boolean as independent proof.
- One-host control still escalates, but with `insufficient_corroboration`, because the fixture is two Sysmon-only facts and host corroboration is not met (`gate.py:362-366`). That is expected for this fixture and is the contrast that makes the two-host flag specific.
- Both arms run the same executor with no arm parameter. Prescribed.
- Queue item `eval-kernel-13-thr-multi-host` remains `in_progress` (implementer packet: do not mark done).
- `memory-bank/activeContext.md` still says Tasks 1–12 done / next is Task 13. Status-file updates are allowed, not required for this verifier.
