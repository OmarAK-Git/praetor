# Code review — eval-kernel-06-gov-feed-unhealthy (Task 6)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 6 only (`gov.feed_unhealthy_blocks_contain`). Sprint 1 gate and remaining IDs ignored.
**Diff reviewed:** commit `22fa79e` (`evals/e2e_kernel.py`, `evals/e2e_scenarios/gov.feed_unhealthy_blocks_contain.yaml`, `tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py`) plus current disk contents of those files. Working tree matches `22fa79e` for the product files.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 6 (through commit, before Task 7)
- `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md` §5 `gov.feed_unhealthy_blocks_contain`
- `.workflow/eval-kernel-06-gov-feed-unhealthy/packets/code-reviewer.md`
- `.workflow/eval-kernel-06-gov-feed-unhealthy/plan.md` acceptance
- Playbook AG-0097 (allowlist before auto_contain under default-deny)
- Playbook fixture `evals/scenarios/revocation_feed_unhealthy_blocks_autocontain.yaml` + `evals/harness.py` `_run_revocation_feed_degraded_mode`

## Blocking findings

None.

## Checks

| Check | Result |
|---|---|
| Unhealthy feed blocks `auto_contain`, allows `standard_review` | `_run_gov_feed_unhealthy` runs two `process_alert_intake` calls on one store (`AUTO_CONTAIN` then `STANDARD_REVIEW`). Pins: escalate + `revocation_feed_unhealthy`, then `standard_review`. Gate order in `src/praetor/policy/gate.py` is containment policy first, then feed block (only on `AUTO_CONTAIN`; other proposals pass through at L340). |
| Production intake, not PolicyGate-only | `process_alert_intake` is the call site (`evals/e2e_kernel.py:225-231`). No `evaluate_policy_gate` import or call in `e2e_kernel.py`. Intake loads the active snapshot (`orchestrator.py:273`) and evaluates the gate internally. |
| Same degraded-mode contract as playbook fixture | `_apply_policy_setup` applies `feed_unhealthy: true` (`harness.py:910-913`). Allowlist is persisted after setup so the feed pin is reachable (see justified deviation). Same host bundle + two dispositions as the Task 6 snippet; playbook runner uses `evaluate_policy_gate` + a second host for review — E2E correctly uses intake instead. |
| Both arms pass on FakeProvider | YAML pins both arms `provider: fake` with identical expected escalate / `revocation_feed_unhealthy` / `standard_review`. Test asserts `{old_build, new_build}` and `status=pass`. Fresh run: 1 passed. |
| YAML / test match Task 6 snippet | `gov.feed_unhealthy_blocks_contain.yaml` and `test_gov_feed_unhealthy_blocks_contain.py` match the plan Step 3 / Step 1 text. Scorecard pins are the three named keys. `theater_detector: stipulated_capability` stays clean (gov ID is not in `CAPABILITY_QUALITY_IDS`). |
| Writes only allowed files | `22fa79e` touches only the three Task 6 product paths. No `src/praetor/**`, no OM scenario edits, no Task 7–19 YAML. |
| Extra product scope | None beyond the allowlist persist required to make the plan YAML's `containment_allow` actually take effect (harness.py is not an allowed file). Sprint 1 gate not run. |
| Verification (this review) | `pytest tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py -q` → 1 passed; `ruff check` clean; `mypy evals/e2e_kernel.py` clean. |

YAML, test, dispatch, and intake loop match the approved Task 6 snippet. Justified deviation: after `_apply_policy_setup`, the executor persists `allowlist_containment_policy` from `containment_allow` (`evals/e2e_kernel.py:207-218`). `_apply_policy_setup` only applies that allowlist when `proposed_disposition == auto_contain` (`harness.py:574-575`); the Task 6 YAML has two intakes and therefore omits `proposed_disposition`. Without the persist, default-deny returns `containment_policy_escalation_required` before the feed check (gate L408-413 vs L424-429), so the pin would be the wrong flag. This is the same persist `_run_revocation_feed_degraded_mode` already does (`harness.py:1214-1220`) and is required by AG-0097. Disk files match `22fa79e`.

## Non-blocking notes

1. **`used_process_alert_intake` is self-attested** (`evals/e2e_kernel.py:240`). The executor hardcodes `True` after a successful intake return; the test asserts that key. A stubbed dict with the same four observed fields would keep the test green. This is the plan snippet. The source path is the real pin — do not treat the flag as independent proof.

2. **Allowlist persist is necessary and not in the pasted executor.** Plan Step 3 omitted it; the YAML still ships `containment_allow`. Copying the snippet literally would fail Step 4 or pass for the wrong fault. Later two-disposition gov pins should keep this persist (or set a temporary `proposed_disposition` only for setup), not copy the raw snippet.

3. **Dispatch does not require `realm == governance`** (`evals/e2e_kernel.py:93`). `gov.never_contain_live_shape` checks both; this ID checks `scenario_id` only. The YAML realm is `governance`. Inconsistency only.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Self-attested intake flag** (`evals/e2e_kernel.py:240`, `tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py:22`). Track only. Plan-faithful. Same cargo-cult risk as Task 5.

2. **Silent skip if no active snapshot** (`evals/e2e_kernel.py:208`). If `fetch_active_snapshot` is `None`, allowlist is skipped and intake then raises. `_open_activated_store` always activates a snapshot today. Track only; a hard `RuntimeError` would match intake's own guard.
