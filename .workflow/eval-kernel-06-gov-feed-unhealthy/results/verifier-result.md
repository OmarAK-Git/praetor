# Verifier result — eval-kernel-06-gov-feed-unhealthy (Task 6)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 6 is done — kernel executor runs `gov.feed_unhealthy_blocks_contain` through production `process_alert_intake` (not a PolicyGate-only shortcut); unhealthy revocation feed blocks `auto_contain` with `revocation_feed_unhealthy` and still allows `standard_review`; both `old_build` and `new_build` pass on FakeProvider; setup uses the same degraded-mode contract as `evals/scenarios/revocation_feed_unhealthy_blocks_autocontain.yaml`.

Implementer results (`1 passed`, ruff/mypy green, `used_process_alert_intake: True`) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Both arms pass on FakeProvider | **met** | YAML pins both arms `provider: fake` with identical expected escalate / `revocation_feed_unhealthy` / `standard_review` (`evals/e2e_scenarios/gov.feed_unhealthy_blocks_contain.yaml:15-28`). Fresh `test_feed_unhealthy_blocks_contain_both_arms` passed. Independent kernel dump: both arms `status=pass`, `failure_class=none`, `provider=fake`. Judgment object is `_CountingJudgmentProvider` (`evals/e2e_kernel.py:222-224`) as prescribed by the Task 6 snippet and as `evals/harness.py:737-739` does for bundle `engine_intake`. Scorecard `provider` is the YAML `fake` pin, not a live Vertex path. |
| Unhealthy feed blocks `auto_contain` and allows `standard_review` | **met** | `_run_gov_feed_unhealthy` (`evals/e2e_kernel.py:233-234`) runs two `process_alert_intake` calls on one store (`AUTO_CONTAIN` then `STANDARD_REVIEW`). Fresh scorecard observed: `auto_contain.final_disposition=escalate`, `auto_contain.fault_flags=['revocation_feed_unhealthy']`, `standard_review.final_disposition=standard_review`. Causal probe (same intake path): with `feed_unhealthy` unset, auto_contain becomes `auto_contain` with empty flags — the block is caused by feed health, not a stubbed dict. Gate feed check is `is_feed_actuation_blocked` → `_escalate(..., REVOCATION_FEED_UNHEALTHY, system_fault=True)` (`src/praetor/policy/gate.py:424-429`). Non-`AUTO_CONTAIN` proposals pass through at `gate.py:340-341`. |
| Uses the same degraded-mode contract as the playbook fixture | **met** | Playbook fixture `evals/scenarios/revocation_feed_unhealthy_blocks_autocontain.yaml` sets `feed_unhealthy: true` and expects AC escalate + `revocation_feed_unhealthy` + `system_fault_escalation: true`, SR `standard_review` + empty flags + `system_fault_escalation: false`. E2E YAML uses the same `feed_unhealthy: true` plus `containment_allow` (Task 6 snippet). `_apply_policy_setup` calls `set_feed_unhealthy` (`evals/harness.py:910-913`). Allowlist persist after setup (`evals/e2e_kernel.py:207-218`) matches `_run_revocation_feed_degraded_mode` (`evals/harness.py:1214-1220`) / AG-0097 so the feed pin is reachable under default-deny. Independent edict probe on the production intake path: AC `escalate ['revocation_feed_unhealthy'] sfe True`; SR `standard_review [] sfe False`. E2E uses `process_alert_intake` instead of playbook `evaluate_policy_gate` — that is the Task 6 interface. |
| Verifier checks only Task 6 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No remaining-13 YAML required; no Sprint 1 / phase-exit suite run. Queue item still `in_progress`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py -q` | **0** | `.` — 1 passed in 1.36s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~1.4s) is consistent with real store + two intakes (kernel also loads Task 5 `gov.never_contain_live_shape` and emits missing-ID error rows; the test filters to this ID).

Product files: `git diff 22fa79e` empty for `evals/e2e_kernel.py`, `evals/e2e_scenarios/gov.feed_unhealthy_blocks_contain.yaml`, `tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py`. HEAD is `22fa79e` (`feat(evals): pin gov.feed_unhealthy_blocks_contain on intake`). `src/praetor/`, `evals/harness.py`, `evals/scenarios/`, `evals/outcome_matrix.py` clean.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Production intake, not PolicyGate-only | **met** | `evals/e2e_kernel.py` has no `evaluate_policy_gate` import or call. Gate runs only inside production intake (`src/praetor/engine/orchestrator.py:444`). Pins come from `blocked.edict` / `review.edict` after real intake returns (`evals/e2e_kernel.py:236-240`). |
| Writes only allowed files | **met** | `22fa79e` product paths are the three allowed code/test/YAML files. No `src/praetor/**`, no OM scenario edits, no Task 7–19 YAML. |
| Outcome Matrix / playbook fixture unchanged | **met** | `git status --short -- evals/harness.py evals/scenarios evals/outcome_matrix.py src/praetor` empty. Playbook OM scenario still `runner: revocation_feed_degraded_mode`. |

## Independent probes (not in packet)

- Loader: `list_e2e_scenarios` returns `gov.feed_unhealthy_blocks_contain` with `runner=e2e_kernel`, realm `governance`, pins exactly the three Task 6 keys, `theater_detector=stipulated_capability`.
- Fresh `run_e2e_kernel` dump: both arms pass; observed includes `used_process_alert_intake: True` and the three pins; notes empty (theater did not trip).
- Causal intake probe (same helpers as the executor):
  - baseline (`feed_unhealthy` + allowlist persist): AC `escalate ['revocation_feed_unhealthy'] sfe True`; SR `standard_review [] sfe False` — playbook fixture contract at edict level.
  - `feed_unhealthy=False` + allowlist: AC `auto_contain []` — pin is feed-caused.
  - `feed_unhealthy=True` without allowlist persist: AC `escalate ['containment_policy_escalation_required']` — extra persist is load-bearing; without it the scorecard would fail or pass for the wrong flag.
- Justified deviation vs pasted plan executor: after `_apply_policy_setup`, persist `allowlist_containment_policy` from `containment_allow`. `_apply_policy_setup` only applies that allowlist when `proposed_disposition == auto_contain` (`evals/harness.py:574-575`); Task 6 YAML omits `proposed_disposition` because it runs two intakes. Same persist as `_run_revocation_feed_degraded_mode`. Required by AG-0097.
- `_run_gov_feed_unhealthy` ignores `arm`; both arms execute the same intake. Prescribed: identical expected pins on both arms.
- Dispatch is ID-gated (`evals/e2e_kernel.py:93-94`); does not also require `realm == governance` (Task 5 dispatch does). YAML realm is `governance`. Inconsistency only.

## Gaps

None that fail Task 6 acceptance.

Residual (non-blocking, not Task 6 AC failures):

- `used_process_alert_intake` is hardcoded `True` after intake returns (`evals/e2e_kernel.py:240`). Plan-faithful. Do not treat that key as independent proof; the edict pins plus the causal probe are the proof.
- Scorecard does not pin `standard_review.fault_flags` or `system_fault_escalation`. Playbook fixture does. Live edicts still match the playbook (empty SR flags, AC `sfe=True`, SR `sfe=False`).
- Allowlist persist is necessary and not in the pasted Task 6 executor. Copying the snippet literally would fail Step 4 or pass for `containment_policy_escalation_required`. Later two-disposition gov pins should keep this persist.
- Queue item `eval-kernel-06-gov-feed-unhealthy` remains `in_progress` (implementer packet: do not mark done).
