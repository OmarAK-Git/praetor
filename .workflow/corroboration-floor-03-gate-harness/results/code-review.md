# Code review — corroboration-floor-03-gate-harness (re-review)

**Verdict:** PASS

**Reviewer:** code-reviewer (fresh context, post-remediation)
**Scope:** Task 03 allowed files — harness YAML, policy/engine/correlation tests, `evals/run_phase3_gate.py`, synthetic fixture
**Spec:** `.workflow/corroboration-floor-03-gate-harness/plan.md` + implementer packet locked behavior

## Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Harness `insufficient_corroboration` — sole ambiguous host citation → escalate / `insufficient_corroboration` / SFE=false | OK | `evals/scenarios/insufficient_corroboration.yaml`; `tests/fixtures/synthetic/host_sole_ambiguous_insufficient.json`; covered by `tests/evals/test_eval_harness.py` (78 passed) |
| Single-provenance host `auto_contain` no longer escalates solely for `insufficient_corroboration` | OK | `test_host_single_cited_provenance_auto_contains`, `test_two_sysmon_citations_same_path_auto_contains`, `test_uncited_cross_host_noise_does_not_capture_target`, correlation `test_two_sysmon_facts_authorize_host_contain_via_policy_gate`, phase3 gate single-sysmon check |
| Touched policy/engine/eval/correlation tests updated and green | OK | `pytest tests/policy/ -q` → **70 passed**; task verification bundle → **78 passed**; `tests/evals/test_phase3_regression_gate.py` → **15 passed** |

## DEC-065 locked-behavior checklist

| Pin | Status | Evidence |
|---|---|---|
| Single non-ambiguous provenance host citation may authorize | OK | `test_host_single_cited_provenance_auto_contains`; `test_uncited_cross_host_noise_does_not_capture_target` → `AUTO_CONTAIN` on `INCIDENT_HOST_ID`; `evals/run_phase3_gate.py:355-374` |
| Sole ambiguous anchoring cite still fails host corroboration | OK | Harness YAML + fixture; `test_sole_ambiguous_cited_fact_escalates`; `test_host_corroboration_helper_pass_does_not_bypass_sole_ambiguous_gate`; correlation `test_ambiguous_sysmon_only_resolves_host_via_policy_gate`; engine intake test; phase3 gate `host_sole_ambiguous` check (`run_phase3_gate.py:400-407`) |
| Harness uses sole ambiguous host citation (not ≥2-path) | OK | Single `ambiguity_flag=true` fact cited on `host_id`; description matches failure mode |
| Account tests accept ≥1 fact when gate enabled | OK | `test_policy_gate.py` SID+single fact → `account_containment_disabled`; correlation docstring + `meets_account_corroboration` assertions at `test_correlator_identity_compliance.py:247` |

## Prior findings — remediation status

| Prior finding | Severity | Status |
|---|---|---|
| `test_citation_anchored_host_targeting.py` expected old single-cite `insufficient_corroboration` | Critical | **Fixed** — now expects `AUTO_CONTAIN`, empty fault flags, directive on `INCIDENT_HOST_ID` |
| `evals/run_phase3_gate.py` enforced sysmon-only `insufficient_corroboration` | Important | **Fixed** — permissive allowlist + single non-ambiguous sysmon → `AUTO_CONTAIN`; sole ambiguous → `ESCALATE` + `insufficient_corroboration` |
| Stale correlation account docstring | Minor | **Fixed** — `test_correlator_identity_compliance.py:247` references DEC-065 ≥1 floor |

## Findings

No Critical or Important findings. Prior blockers are resolved.

### Minor (track)

1. **Task verification commands still omit full `tests/policy/`**
   - Plan runs three policy modules only; full suite is green (70 passed) but a future regression in an untested policy file would not be caught by the task command.
   - **Fix (process):** Add `pytest tests/policy/ -q` to task verification commands before sprint gate.

2. **Zero-anchor harness scenario not added**
   - Packet allows zero anchors “if harness runner can express that”; AC only requires sole ambiguous. Non-blocking.

## What was checked

- `git diff` for task 03 scope (harness YAML, policy/engine/correlation tests, `evals/run_phase3_gate.py`, synthetic fixture)
- `evals/scenarios/insufficient_corroboration.yaml` vs DEC-065 OM row semantics
- `tests/fixtures/synthetic/host_sole_ambiguous_insufficient.json` vs harness setup (`host_id: ws-01`, cite `host-ambiguous-only`)
- `pytest tests/policy/ -q` → 70 passed
- `pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/engine/test_gate_target_ownership.py tests/evals/test_eval_harness.py -q` → 78 passed
- `pytest tests/evals/test_phase3_regression_gate.py -q` → 15 passed
- `pytest tests/policy/test_citation_anchored_host_targeting.py::test_uncited_cross_host_noise_does_not_capture_target -q` → 1 passed
- `ruff check tests/policy tests/engine/test_gate_target_ownership.py` → passed
- `rg INSUFFICIENT_CORROBORATION` across `tests/policy`, `tests/engine`, `tests/correlation`, `evals/` — remaining assertions are sole-ambiguous or negative (not-in) cases only

## Rationale

Remediation correctly closes the prior Critical/Important gaps. Harness, policy gate integration tests, engine intake, correlation suite, citation-anchored targeting, and phase3 gate script all align with DEC-065: single non-ambiguous host citation authorizes; sole ambiguous anchoring cite still fails with `insufficient_corroboration`. Full `tests/policy/` is green. Task acceptance criteria are met.
