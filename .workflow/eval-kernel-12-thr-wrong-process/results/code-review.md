# Code review — eval-kernel-12-thr-wrong-process (Task 12)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 12 only (`thr.valid_cite_wrong_process`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `088477a` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/thr.valid_cite_wrong_process.yaml`, `tests/evals/e2e/test_thr_valid_cite_wrong_process.py`) plus current disk contents of those files. HEAD is `088477a`; working tree matches that commit for the three product paths. `src/praetor/**` has an empty diff vs parent.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 12 (through commit, before Task 13)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `thr.valid_cite_wrong_process`
- `.workflow/eval-kernel-12-thr-wrong-process/packets/code-reviewer.md`
- `.workflow/eval-kernel-12-thr-wrong-process/plan.md` acceptance

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Miss is recorded | `_run_thr_wrong_process` correlates `tests/fixtures/sysmon/process_chain.json` + the 4624 fixture, cites parent `{1111…}` via `skeleton_model_judgment` + `CitedEvidenceRef`, and sets `cite_to_subject` from `subject_fact.evidence_id in cited_ids`. Subject is child `{2222…}`. Both arms pin `cite_to_subject: false`. Dispatch wired at `e2e_kernel.py:107-108`. |
| Citations resolve | `citations_valid` is `validate_evidence_citations(judgment, correlated.bundle).valid`, not a hardcoded true. Parent Sysmon facts carry `process_name`; `field_path="process_name"` is a resolvable path. Pin is `true` on both arms. |
| Authority does not treat valid cite as right subject | Observed `authority_treats_valid_cite_as_right_subject` is `validation.valid and cite_to_subject`. With valid=true and miss recorded, the pin is `false`. No PolicyGate / `process_alert_intake` path; that is the approved Task 12 snippet, not Sprint 2 scoring. |
| No McNemar / Sprint 2 primary | `rg` over `evals/` finds no McNemar / scipy / statsmodels. `cite_to_subject_primary_earned` stays hardcoded `False` in existing `TheaterContext` construction. No new primary metric, no arm comparison. |
| Both arms pass Sprint 1 authority pin | YAML pins both arms `provider: fake` with the three named keys. Test asserts `{old_build, new_build}`, `status=pass`, and the three observed bools plus subject GUID. Fresh run: 1 passed. |
| YAML / test / executor match Task 12 snippet | YAML and test match Step 3 / Step 1 text. Executor matches Step 3 except unused `ModelJudgment` import omitted (plan listed it; it is unused). `REPO_ROOT` imported from `evals.harness`. `_load_fixture_events` added as prescribed. Scorecard pins are the three named keys; `subject_process_guid` / `cited_evidence_id` stay observed-only. |
| Writes only allowed files | `088477a` is the three Task 12 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 13–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_load_fixture_events` + `_run_thr_wrong_process` are the approved additive surface. |
| Verification (this review) | `pytest tests/evals/e2e/test_thr_valid_cite_wrong_process.py -q` → 1 passed in 2.31s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and citation/graph calls match the approved Task 12 snippet. Disk files match `088477a`. The miss is load-bearing via real `validate_evidence_citations` + evidence-id inequality; Sprint 2 McNemar is absent.

## Non-blocking notes

1. **`authority_treats_valid_cite_as_right_subject` is a derived AND** (`evals/e2e_kernel.py:394-396`). Given the other two pins, it cannot be true on this scenario. It is not an independent PolicyGate / authority-layer probe. Prescribed.

2. **Graph is a presence assert, not a parent join** (`evals/e2e_kernel.py:368-371`). `assemble_process_relationships` is called; `graph.parent_of(subject_guid)` is never used to select the cited fact. The wrong-process cite is the YAML `cite_process_guid`. Fixture `{1111…}` is the parent of `{2222…}`. Plan-shaped.

3. **Test does not pin `cited_evidence_id` or parent GUID** (`tests/evals/e2e/test_thr_valid_cite_wrong_process.py:19-24`). A stub that cited any non-subject resolvable fact would keep the prescribed asserts green. Executor does use `cite_process_guid`. Prescribed test.

4. **`gate_scored_as_judgment` cannot trip on this path.** Detector needs `scorecard_is_quality_pass` and `scored_layer=policy_gate` in `excerpt_blob`. This ID is not a capability-quality scenario; `run_e2e_scenario` also hardcodes `excerpt_blob=""` (`e2e_kernel.py:126`). Plan-faithful; the theater name is not independent proof.

5. **Dispatch does not require `realm == threat`** (`evals/e2e_kernel.py:107`). Same pattern as Tasks 6–11. YAML realm is `threat`. Inconsistency only.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Derived authority pin** (`evals/e2e_kernel.py:394-396`). Track only. Sprint 2 should not treat this AND as the cite-to-subject primary; the primary is the `cite_to_subject` boolean already recorded.

2. **Graph join unused** (`evals/e2e_kernel.py:368-371`). Track only. A later cleanup may assert `graph.parent_of(subject_guid).process_guid == cite_guid` so the fixture relationship is pinned, not just subject presence.

3. **No negative row that a subject-cite is `failure_class=harness`** (`evals/e2e_kernel.py:113-116`). Classification is the existing kernel pin loop, not new Task 12 logic. Track only; do not treat the passing test as proof of the mismatch path.
