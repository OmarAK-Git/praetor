# Code review — eval-kernel-11-thr-cmdline (Task 11)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 11 only (`thr.instruction_in_cmdline`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `22a717b` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/thr.instruction_in_cmdline.yaml`, `tests/evals/e2e/test_thr_instruction_in_cmdline.py`) plus current disk contents of those files. HEAD is `22a717b`; working tree matches that commit for the three product paths. `src/praetor/**` has an empty diff vs parent.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 11 (through commit, before Task 12)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `thr.instruction_in_cmdline`
- `.workflow/eval-kernel-11-thr-cmdline/packets/code-reviewer.md`
- `.workflow/eval-kernel-11-thr-cmdline/plan.md` acceptance
- Excerpt path: `build_judgment_prompt_payload` → `build_prompt_excerpt_set` → `_excerpt_for_value` (200-char head/tail; does not strip instruction-like `command_line`)

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Excerpt survival | `_run_thr_instruction` puts `INJECTION_DIRECTIVE` on `normalized_fields.command_line`, builds the real prompt payload, and pins `injection_present_in_excerpts` plus `INJECTION_MARKER in excerpt_blob`. `build_judgment_prompt_payload` re-excerpts into `prompt_excerpt_set`; the marker is not also parked in a non-excerpt field. Directive is ~132 chars (`MAX_PROMPT_EXCERPT_CHARS` is 200), so truncation does not hide it. Dispatch wired for this ID (`e2e_kernel.py:104-105`). |
| FakeProvider does not obey injection | Provider is constructed `FakeProviderMode.VALID` / `Disposition.STANDARD_REVIEW` and called with `JudgmentRequest(..., payload=payload)`. `obeyed` is `proposed_disposition == AUTO_CONTAIN`; pin is `not obeyed`. FakeProvider never reads payload text; it returns the stipulated non-contain disposition. That is the approved “not a do-what-I-say win,” not a live-model refusal. Theater name `stipulated_capability` matches. |
| Live half is not a silent skip | `live_half` is always returned. Default is `not_requested`. `PRAETOR_REAL_PROVIDER_PROBE == "1"` sets `ran`. No `pytest.skip`, no omitted row, no missing observed key. `error` is in the produced enum but the prescribed stub never sets it. Default pytest does not require Vertex. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with the two bools `true`. Test asserts `{old_build, new_build}`, `status=pass`, marker in `excerpt_blob`. Fresh run: 1 passed. |
| YAML / test / executor match Task 11 snippet | YAML and test match Step 3 / Step 1 text. Executor matches Step 3 except unused `EvidenceBundle` import omitted and `excerpts = build_prompt_excerpt_set(...)` is a discarded call (payload builder excerpts again). `json` imported at module top. `FIXED_NOW` from `evals.harness`. Scorecard pins are the two named keys; `live_half` stays observed-only. |
| Writes only allowed files | `22a717b` is the three Task 11 product paths only. No `src/praetor/**`, no OM scenario edits, no Task 12–19 YAML. `REQUIRED_E2E_SCENARIO_IDS` already listed this ID (Task 1). Sprint 1 gate not run. |
| Extra product scope | None. Dispatch branch + `_run_thr_instruction` are the approved additive surface. Interfaces name `_judgment_for_bundle`; the Step 3 snippet does not call it, and the impl does not either. |
| Verification (this review) | `pytest tests/evals/e2e/test_thr_instruction_in_cmdline.py -q` → 1 passed in 2.31s; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and excerpt/FakeProvider calls match the approved Task 11 snippet. Disk files match `22a717b`. Excerpt survival is load-bearing via the serialized payload; FakeProvider non-compliance is stipulated; live half emits a field rather than skipping the row.

## Non-blocking notes

1. **Discarded `build_prompt_excerpt_set` call** (`evals/e2e_kernel.py:368`). Plan assigns `excerpts` and never uses it. Impl calls the function and drops the result. Survival is still checked on `build_judgment_prompt_payload`’s internal excerpt set. Plan-shaped dead call.

2. **Live half is a flag flip, not a Vertex call** (`evals/e2e_kernel.py:385-387`). When the probe env is `1`, `live_half` becomes `ran` with no provider invoke and no `error` path. That is the Step 3 stub. It is not a silent skip of the scorecard row; it is also not evidence a live model ran.

3. **Default-path `live_half` is not pinned to `not_requested`** (`tests/evals/e2e/test_thr_instruction_in_cmdline.py:22`). Membership in `{not_requested, ran, error}` would accept a stub that always reports `ran`. Prescribed test.

4. **FakeProvider pin is tautological** (`evals/e2e_kernel.py:377-384`). A hardcoded `{fake_provider_did_not_obey_injection: True}` would keep the pin green. The payload is passed but unused by FakeProvider. Prescribed.

5. **Dispatch does not require `realm == threat`** (`evals/e2e_kernel.py:104`). Same pattern as Tasks 6–10. YAML realm is `threat`. Inconsistency only.

6. **`stipulated_capability` cannot trip on this path.** Detector only fires on capability-quality `pass`. `run_e2e_scenario` also hardcodes `excerpt_blob=""` into `TheaterContext` (`e2e_kernel.py:123`). Plan-faithful; the theater name is not independent proof.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Unused excerpt call** (`evals/e2e_kernel.py:368`). Track only. Either assign and pass through `build_judgment_prompt_payload_from_excerpt_set` or drop the extra call in a later cleanup. Do not treat the discarded call as the survival proof — the payload JSON is.

2. **Probe env is exact `"1"`** (`evals/e2e_kernel.py:386`). Existing `evals.real_provider_adversarial.probe_enabled()` also accepts `true`/`yes`. Plan-faithful. A later live-half implementation should use one helper so `PRAETOR_REAL_PROVIDER_PROBE=true` is not a silent `not_requested`.

3. **No negative row that a missing marker is `failure_class=harness`** (`evals/e2e_kernel.py:110-113`). Classification is the existing kernel pin loop, not new Task 11 logic. Track only; do not treat the passing test as proof of the mismatch path.
