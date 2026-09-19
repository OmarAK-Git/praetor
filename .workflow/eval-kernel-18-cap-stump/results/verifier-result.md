# Verifier result — eval-kernel-18-cap-stump (Task 18)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 18 is done — `path_a_fact_count_stump` and `stump_pair` exist and emit McNemar-ready paired outcomes; `quality_win_claimed` is false; `new_build` is `pending`, not `pass`; `old_build` is recorded honestly as pending-new (honesty `pass` on pairs emitted + no quality-win claim); disposition-vs-stump is not a Sprint 1 or Sprint 2 primary.

Implementer results (`3 passed`, ruff/mypy green, McNemar-ready / no-quality-win / pending claims) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `path_a_fact_count_stump` and `stump_pair` exist and are McNemar-ready | **met** | Both callables live in `evals/stump.py:12-42`. Threshold: `>= 2` → `malicious`, else `benign`. `stump_pair` returns `stump_prediction`, `stump_correct`, `model_bucket`, `model_correct` plus `bag_id` / `frozen_label` / `path_a_fact_count`. Unit test pins those four keys on `standard_review` → `model_bucket="benign"`, `model_correct=False` (`tests/evals/test_stump.py:11-21`). Independent live `run_e2e_kernel` dump (this session): both arms observed `stump_prediction=malicious`, `stump_correct=True`, `model_bucket=benign`, `model_correct=False`, `path_a_fact_count=3`. Independent `correlate_telemetry` on the locked fixtures also yields 3 Path A facts; `stump_pair(..., path_a_fact_count=3, model_proposed="standard_review")` matches the kernel rows. No McNemar cell, scipy, or inferential p-value is implemented in `evals/` (only pre-existing spike writeup under `tools/`). |
| `new_build` is `pending`, not `pass`; no quality-win assertion | **met** | Live dump: `new_build.status=pending`, `failure_class=none`. Pending override is `CAPABILITY_QUALITY_IDS` + `arm == "new_build"` + `status != "fail"` (`evals/e2e_kernel.py:154-160`). This ID is in `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-17`). `quality_win_claimed` is hardcoded `False` in `stump_pair` (`evals/stump.py:41`); YAML pins `false` on both arms (`cap.stump_parity_guard.yaml:16,20`). Live observed `quality_win_claimed=false` on both arms. `model_correct` is never consulted for status. `cite_to_subject_primary_earned` stays hardcoded `False` on this path (`e2e_kernel.py:147`). E2E asserts `rows["new_build"].status == "pending"` (`test_cap_stump_parity_guard.py:23`). Independent `validate_scorecard_row` accepts this ID + `new_build` + `pending`; rejects the same ID on `old_build` + `pending`. |
| `old_build` recorded honestly (`new≈stump` or pending new) | **met** | Honest Sprint 1 alternative used: **pending new**, not a documented `new≈stump` quality claim. Live `old_build`: `status=pass`, `failure_class=none` — honesty pin only (paired outcomes emitted + `quality_win_claimed` false), matching the Task 18 interface (`docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 18). On this fixture the pair is stump-correct / model-incorrect (`standard_review` vs `frozen_label=malicious`); that mismatch does not flip status and is not reported as `new≈stump`. `_quality_pass_forbidden("cap.stump_parity_guard", "pass")` returns `False` (`e2e_kernel.py:74-77`; live probe this session), so `stipulated_capability` does not treat the honesty pass as a quality pass. Live theater `notes=""`. |
| Verifier checks only Task 18 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py -q` | **0** | `...` — 3 passed in 4.80s (no skips) |
| `ruff check evals/stump.py evals/e2e_kernel.py tests/evals/test_stump.py tests/evals/e2e/test_cap_stump_parity_guard.py` | **0** | All checks passed |
| `mypy evals/stump.py evals/e2e_kernel.py` | **0** | Success: no issues found in 2 source files |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~4.8s) is consistent with real kernel load (all YAMLs; the test filters to this ID). Count is from the live `-q` run, not `--collect-only` (GR-0006): 2 unit tests + 1 e2e pin.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Disposition-vs-stump is not treated as a Sprint 1 or Sprint 2 primary | **met** | No McNemar / scipy / statsmodels / α / T=1.0 inferential arm in `evals/`. `cite_to_subject_primary_earned` is hardcoded `False` for this executor (`e2e_kernel.py:147`). Status is pin-match then pending override; `model_correct` and `stump_correct` never set `status`. YAML description forbids “judgment beats stump” (`cap.stump_parity_guard.yaml:4`). `quality_win_claimed` cannot become `True`. |
| `quality_win_claimed` is false | **met** | Hardcoded `False` (`evals/stump.py:41`). YAML pins false. Unit + e2e assert `is False`. Live kernel rows: `false` on both arms. |
| `new_build` is pending | **met** | Live `new_build.status == "pending"`. E2E asserts the same. Scorecard accepts pending only for this ID (and baseline) on `new_build`. |

## Independent probes (not in packet)

- Fresh `run_e2e_kernel` dump: exactly 2 rows for `cap.stump_parity_guard`. `old_build=pass/none`, `new_build=pending/none`. Observed extras: `bag_id=cap.stump_parity_guard`, `path_a_fact_count=3`, `frozen_label=malicious`, `stump_prediction=malicious`, `stump_correct=True`, `model_bucket=benign`, `model_correct=False`, `quality_win_claimed=False`.
- Direct `correlate_telemetry` on `tests/fixtures/sysmon/process_chain.json` + `tests/fixtures/security/successful_logon_4624.json` at the locked anchor → 3 facts; `path_a_fact_count_stump(3) == "malicious"`; live `stump_pair` matches kernel observed.
- `_quality_pass_forbidden("cap.stump_parity_guard", "pass")` → `False`; same for `"pending"`. `stipulated_capability` trips iff `scorecard_is_quality_pass=True` (live: quality=False → clean; quality=True → trip `"FakeProvider proposed_disposition scored as capability quality pass"`).
- `validate_scorecard_row`: this ID + `new_build` + `pending` accepted; this ID + `old_build` + `pending` raises `ScorecardValidationError`.
- `cap.stump_parity_guard` is in `CAPABILITY_QUALITY_IDS`.

## Gaps

None that fail Task 18 acceptance.

Residual (non-blocking, not Task 18 AC failures):

- Happy-path e2e would accept a stubbed observed dict with `quality_win_claimed=False`, the two boolean keys present, `path_a_fact_count >= 1`, plus the existing pending override (`tests/evals/e2e/test_cap_stump_parity_guard.py:17-23`). Prescribed Step 1. This session ran the live executor/`stump_pair`/`correlate_telemetry` path, so the committed key-presence asserts are not the only proof. Pair *values* are pinned only in the unit test on a synthetic `path_a_fact_count=2` call.
- `quality_win_claimed` cannot become true even if `model_correct` is true (`evals/stump.py:41`). Correct for Sprint 1. Honesty then rests on `new_build=pending` and the hardcoded flag, not on an asserted stump/model disagreement.
- Executor copies Task 17 bag construction instead of calling `_run_cap_baseline` (`evals/e2e_kernel.py:424-469`). Plan-faithful enough for this pin; drift risk if Task 17’s bag path later changes.
- Queue item status was not updated (implementer packet: do not mark done).
