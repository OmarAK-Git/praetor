# Code review — eval-kernel-13-thr-multi-host (Task 13)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 13 only (`thr.ambiguous_multi_host_target`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `919897b` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/thr.ambiguous_multi_host_target.yaml`, `tests/evals/e2e/test_thr_ambiguous_multi_host_target.py`) plus current disk contents of those files. HEAD is `919897b`; working tree matches that commit for the three product paths. `src/praetor/**` has an empty diff vs parent.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 13 (through commit, before Task 14)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `thr.ambiguous_multi_host_target`
- `.workflow/eval-kernel-13-thr-multi-host/packets/code-reviewer.md`
- `.workflow/eval-kernel-13-thr-multi-host/plan.md` acceptance
- Production path: `process_alert_intake` → `evaluate_policy_gate` → `resolve_containment_target` → `resolve_host_target_from_citations` (≥2 cited hosts → `ambiguous=True` → `ambiguous_containment_target`)

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Production `process_alert_intake` (not PolicyGate-only) | `_run_thr_multi_host` calls `process_alert_intake(store, judgment_provider=..., stamp_backend=..., alert_identity=..., evidence_bundle=bundle)` (`evals/e2e_kernel.py:374-381`). No `evaluate_policy_gate` import or call in `e2e_kernel.py`. Gate evaluation happens only inside orchestrator intake (`src/praetor/engine/orchestrator.py`). Same helper stack as the OM `multi_host_target_ambiguity` pin: `_open_activated_store`, `_resolve_policy_bundle` (`bundle: synthetic_fixture`), `_judgment_for_bundle(..., cited_refs=refs)`, `_CountingJudgmentProvider`, `_stamp_backend`. `correlate` defaults to `True`; `_resolve_intake_evidence_bundle` returns the provided fixture bundle unchanged. |
| Two distinct cited hosts escalate `ambiguous_containment_target` | YAML citations are `host-a-1` / `host-b-1` on `host_id`, same as `evals/scenarios/multi_host_target_ambiguity.yaml`. Fixture `tests/fixtures/synthetic/multi_host_two_cited_hosts.json` has `WORKSTATION1` and `WORKSTATION2`, no SID. `extract_account_identity` returns `None` → host fallback from cited facts (`containment_policy.py:156-167`). `len(cited_host_ids) >= 2` → `ambiguous=True` → `gate.py:348-353` `_escalate(..., AMBIGUOUS_CONTAINMENT_TARGET)`. Exact pin `fault_flags == ["ambiguous_containment_target"]` is load-bearing: `_default_auto_contain_citation_refs` on this two-sysmon fixture would cite only `facts[0]`, which cannot produce that flag. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with `final_disposition: escalate` and `fault_flags: [ambiguous_containment_target]`. Test asserts `{old_build, new_build}`, `status=pass`, those two observed keys, and `used_process_alert_intake`. Fresh run: 1 passed. |
| YAML / test / executor match Task 13 snippet | YAML matches Step 3 text. Test matches Step 1 text. Executor matches Step 3 text. Dispatch wired at `e2e_kernel.py:109-110`. Scorecard pins are the two named keys; `used_process_alert_intake` stays observed-only. |
| Writes only allowed files | `919897b` is the three Task 13 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 14–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_run_thr_multi_host` are the approved additive surface. |
| Verification (this review) | `pytest tests/evals/e2e/test_thr_ambiguous_multi_host_target.py -q` → 1 passed in 2.67s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and intake/citation wiring match the approved Task 13 snippet. Disk files match `919897b`. Escalation is produced by production citation-anchored targeting on two cited hosts, not a PolicyGate-only shortcut.

## Non-blocking notes

1. **`used_process_alert_intake` is self-attested** (`evals/e2e_kernel.py:385`). The executor hardcodes `True` after a successful intake return; the test asserts that key. A stubbed dict with the same three observed fields would keep `test_ambiguous_multi_host_both_arms` green. This is the plan snippet. The source path is the real pin — do not treat the flag as independent proof.

2. **`stipulated_capability` cannot trip on this path.** Detector only fires on capability-quality `pass`. This ID is not in `CAPABILITY_QUALITY_IDS`; `run_e2e_scenario` also hardcodes `excerpt_blob=""` (`e2e_kernel.py:128`). Plan-faithful; the theater name is not independent proof.

3. **Dispatch does not require `realm == threat`** (`evals/e2e_kernel.py:109`). Same pattern as Tasks 6–12. YAML realm is `threat`. Inconsistency only.

4. **No negative single-host row.** The prescribed test does not assert that citing only `host-a-1` is `failure_class=harness`. Classification is the existing kernel pin loop. The exact `["ambiguous_containment_target"]` equality still fails if citations collapse to one host (that path yields a different flag). Track only.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Self-attested intake flag** (`evals/e2e_kernel.py:385`, `tests/evals/e2e/test_thr_ambiguous_multi_host_target.py:21`). Track only. Plan-faithful. A later static or monkeypatch test could assert `process_alert_intake` is the call site if this keeps getting cargo-culted.

2. **No negative row that a single cited host is `failure_class=harness`** (`evals/e2e_kernel.py:115-118`). Classification is the existing kernel pin loop, not new Task 13 logic. Track only; do not treat the passing test as proof of the mismatch path.
