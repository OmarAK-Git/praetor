# Verifier result — eval-kernel-17-cap-baseline (Task 17)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 17 is done — `cap.baseline_bag_path_a` records a Path A bag (`correlate_telemetry` on Sysmon EventID 1 + Security 4624) fed to `process_alert_intake`; `old_build` is recorded as bag-path `pass`; `new_build` is `pending`, not `pass`; FakeProvider stipulation is not scored as a capability quality pass; no Path B.

Implementer results (`7 passed`, ruff/mypy green, bag-path / pending / no-quality-pass claims) were treated as unevidenced until re-run.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `old_build` is recorded; `new_build` status is `pending`, not `pass` | **met** | Fresh `pytest tests/evals/e2e/test_cap_baseline_bag_path_a.py tests/evals/test_scorecard.py -q` → 7 passed, 0 skipped. Independent `run_e2e_kernel` dump (this session): 2 rows for `cap.baseline_bag_path_a`. `old_build`: `status=pass`, `failure_class=none`, `provider=fake`, `realm=capability`. `new_build`: `status=pending`, `failure_class=none`. Pending override is `CAPABILITY_QUALITY_IDS` + `arm == "new_build"` + `status != "fail"` (`evals/e2e_kernel.py:152-158`). This ID is in `CAPABILITY_QUALITY_IDS` (`evals/scorecard.py:15-17`). `validate_scorecard_row` accepts pending only for quality `new_build`. |
| Bag is `correlate_telemetry` Path A (Sysmon 1 + Security 4624) into `process_alert_intake` | **met** | YAML fixtures are `tests/fixtures/sysmon/process_chain.json` (EventIDs `[1, 1]`) and `tests/fixtures/security/successful_logon_4624.json` (EventID `4624`) (`cap.baseline_bag_path_a.yaml:8-9`). `_run_cap_baseline` calls `correlate_telemetry(sysmon_events=, security_events=, anchor_time=)` then `process_alert_intake(..., sysmon_events=, security_events=, anchor_time=)` (`evals/e2e_kernel.py:375-403`). Intake defaults `correlate=True` and re-runs `correlate_telemetry` in `_resolve_intake_evidence_bundle` when no `evidence_bundle` is passed (`orchestrator.py:121-133,279-286`). Production Path A filters: Sysmon `{1}` (`sysmon.py:22-23`), Security `4624` (`security_log.py:18`). Live `correlate_telemetry` on those fixtures → 3 facts (`sysmon_event_log`, `windows_security_log`, `sysmon_event_log`). Live observed pins: `used_correlate_telemetry=True`, `used_process_alert_intake=True`, `path_a_event_ids=[1, 4624]`. |
| FakeProvider stipulation is not scored as a capability quality pass | **met** | `_quality_pass_forbidden("cap.baseline_bag_path_a", "pass")` returns `False` (`evals/e2e_kernel.py:74-77`; live probe this session). YAML `theater_detector: stipulated_capability`. Detector trips only when `scorecard_is_quality_pass` is true (`evals/theater.py:58-64`). Live probe: quality=False → clean; quality=True → trip `"FakeProvider proposed_disposition scored as capability quality pass"`. Live rows record `proposed_disposition=standard_review` and `frozen_label=malicious` as observed extras, not pins; `notes=""`, no `theater_message`. `alert_identity` is `cap.baseline_bag_path_a` (no `malicious`). |
| Verifier checks only Task 17 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet set. No Sprint 1 / phase-exit suite run. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/evals/e2e/test_cap_baseline_bag_path_a.py tests/evals/test_scorecard.py -q` | **0** | `.......` — 7 passed in 4.20s (no skips) |
| `ruff check evals/e2e_kernel.py tests/evals/e2e/test_cap_baseline_bag_path_a.py` | **0** | All checks passed |
| `mypy evals/e2e_kernel.py` | **0** | Success: no issues found in 1 source file |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (~4.2s) is consistent with real kernel load (all YAMLs; the test filters to this ID). Count is from the live `-q` run, not `--collect-only` (GR-0006): 1 e2e pin + 6 `test_scorecard.py` rows.

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| No Path B import | **met** | `evals/e2e_kernel.py` has no `evals.capability` / `flatten` / `bundle` import (repo grep on that file). Test and YAML have none. Executor does not call a Path B builder. Observed `used_path_b` is `False` (prescribed hardcoded return at `e2e_kernel.py:412`). Confirmation is the import/call-site inspection plus live Path A fact provenances, not that boolean alone. |
| No judgment-quality pass claimed | **met** | Live `new_build.status == "pending"`. `old_build.status == "pass"` is the bag-path pin, not a quality pass (`scorecard_is_quality_pass` forced false for this ID). Theater `stipulated_capability` did not trip. Implementer/result text does not claim FakeProvider quality. |

## Independent probes (not in packet)

- Loader: exactly one `cap.baseline_bag_path_a`; realm `capability`; theater `stipulated_capability`; both arms `provider: fake`; pins `used_correlate_telemetry`, `used_process_alert_intake`, `used_path_b`, `path_a_event_ids`; setup frozen label `malicious` is metadata only.
- Fresh `run_e2e_kernel` dump: 2 rows; `old_build=pass/none`, `new_build=pending/none`; expected pins match; observed extras include stipulated `standard_review` + `malicious` without leaking into `alert_identity`.
- `_quality_pass_forbidden` is ID-specific: baseline/`pass` → `False`; `cap.stump_parity_guard`/`pass` → `True` (Task 18, out of scope; recorded only to show the carve-out is not global).
- `stipulated_capability` trips iff `scorecard_is_quality_pass=True`.
- Direct `correlate_telemetry` on the locked fixtures yields 3 Path A facts (2 Sysmon process-create + 1 Security logon), not an empty or Path B bag.

## Gaps

None that fail Task 17 acceptance.

Residual (non-blocking, not Task 17 AC failures):

- Happy-path pin test would accept a stubbed observed dict with `[1, 4624]` + the three flags plus the existing pending override (`tests/evals/e2e/test_cap_baseline_bag_path_a.py:16-25`). Prescribed Step 1. This session ran the live executor/`correlate_telemetry` path, so the committed booleans are not the only proof.
- `used_path_b` is hardcoded `False` (`evals/e2e_kernel.py:412`). A later flatten import in this executor would not flip the pin. Plan-faithful. No-Path-B confirmation is import/call-site inspection.
- `path_a_event_ids` is derived from raw fixture `EventID`s, not from bag fact fields (`e2e_kernel.py:380-384`). Plan-faithful; current fixtures are EventID 1 and 4624 only.
- `used_correlate_telemetry` is `len(bundle.facts) > 0`, not a call-hook. Plan-faithful. Live fact count on these fixtures is 3.
- `event.get("EventID")` fallback from the plan snippet is omitted. Current fixtures expose top-level `EventID`; `event_field` returns it.
- Queue item status was not updated (implementer packet: do not mark done).
