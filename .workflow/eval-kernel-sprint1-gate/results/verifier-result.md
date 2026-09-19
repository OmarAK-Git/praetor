# Verifier result — eval-kernel-sprint1-gate (Sprint 1 phase-exit, attempt 2)

## Outcome

**pass**

Verify-only phase-exit. No edits to `src/` or `tests/`. Implementer and test-runner transcripts treated as unevidenced; all required commands were re-run this session from `C:\Users\oalan\Praetor`. Attempt 1's mypy failure was not reused — `mypy src evals consumer_sdk` was re-run and exited 0.

Claim restated: Sprint 1 eval kernel is ready to exit — all 15 E2E IDs exist and appear in the scorecard; `python -m evals.harness --all` is green on FakeProvider; governance / design / threat / usability both arms pass; capability quality `old_build` recorded and `new_build` pending; `cap.no_label_leak_ids` both arms pass; full pytest, ruff, and mypy pass; Outcome Matrix still greens; no CBC adapter, AlertEnvelope expansion, or EventID expansion; all 21 task verifier artifacts exist and PASS.

Skeptic verdict on the completion claim: **survives**.

Strongest reason: this session's five required commands all exited 0, and an independent `run_e2e_kernel` dump produced exactly 15 locked IDs × 2 `provider=fake` arms (30 rows) with only the two capability-quality `new_build` rows `pending` and zero fail/error.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| All 15 E2E scenario IDs exist and appear in the scorecard | **met** | Exactly 15 YAML files under `evals/e2e_scenarios/` whose stems equal `REQUIRED_E2E_SCENARIO_IDS` (`evals/e2e_kernel.py:45-63`). Independent `list_e2e_scenarios` this session: yaml_count=15, missing=[], extra=[]. Live `--all` and live `run_e2e_kernel` both emitted both arms for: `cap.baseline_bag_path_a`, `cap.stump_parity_guard`, `cap.no_label_leak_ids`, `gov.never_contain_live_shape`, `gov.feed_unhealthy_blocks_contain`, `gov.recovery_never_contains`, `des.envelope_rejects_extra_fields`, `des.path_b_stays_out_of_src`, `des.evidence_hash_stable`, `thr.instruction_in_cmdline`, `thr.valid_cite_wrong_process`, `thr.ambiguous_multi_host_target`, `use.reconstruct_from_ledger`, `use.progressive_auth_report`, `use.demo_honesty_gate`. |
| `python -m evals.harness --all` is green on FakeProvider | **met** | Fresh this session: exit **0**. 34 OM `[PASS]` + 30 kernel rows (28 `[PASS]`, 2 `[PENDING]`, 0 `[FAIL]` / `[ERROR]`). Independent dump: all 30 rows `provider=fake`; `kernel_exit_code` returns 1 only on fail/error/missing IDs (`evals/e2e_kernel.py:892-902`). Every YAML arm is `provider: fake`. |
| Governance, design, threat, and usability both arms pass | **met** | Live `--all` and live dump: all 12 IDs × 2 arms `status=pass`, `failure_class=none`. |
| Capability quality `old_build` recorded; `new_build` pending; `cap.no_label_leak_ids` both arms pass | **met** | Live dump: `cap.baseline_bag_path_a` old=`pass` / new=`pending`; `cap.stump_parity_guard` old=`pass` / new=`pending`; `cap.no_label_leak_ids` both arms `pass`. Force-pending at `evals/e2e_kernel.py:158-164` after theater; `CAPABILITY_QUALITY_IDS` is exactly those two IDs (`evals/scorecard.py:15-17`). |
| Full pytest, ruff, and mypy pass | **met** | See Commands. mypy attempt-1 errors in `evals/capability/spike_vertex_provider.py` and `evals/capability_spike.py` are gone after `659b249` (narrow isinstance guard + unused `type: ignore` removal). Fresh mypy exit **0**, 155 files. |
| Existing Outcome Matrix harness still greens | **met** | Fresh `python -m evals.harness` (no flags): exit **0**, 34 `[PASS]`, 0 FAIL / PENDING, no kernel IDs printed. Same 34 IDs appear first in `--all`. |
| No CBC adapter, AlertEnvelope expansion, or EventID expansion | **met** | `git log master..HEAD -- src/praetor` empty; `git diff master...HEAD -- src/praetor` empty. `AlertEnvelope` still only `schema_version` + `alert_identity` (`src/praetor/contracts/alert.py:10-18`); `schemas/alert_envelope.json` `additionalProperties: false`. Correlator still Sysmon `{1}` / Security `{4624}` (`src/praetor/correlation/sysmon.py:22-23`, `security_log.py:18-19`). No `*cbc*` source tree; `des.envelope_rejects_extra_fields` exercises existing `extra="forbid"` (`evals/e2e_kernel.py:837-865`). Sprint mypy fix touches only pre-existing spike files under `evals/`. |
| All 21 task verifier artifacts exist and PASS | **met** | Files `eval-kernel-01-scorecard` through `eval-kernel-21-docs-pointer` `results/verifier-result.md` all exist. Each header is `## Outcome` / `**pass**`. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest -q` | **0** | 1220 passed, 2 deselected in 250.82s (0:04:10). No failures. |
| `ruff check src tests evals consumer_sdk` | **0** | All checks passed. |
| `mypy src evals consumer_sdk` | **0** | Success: no issues found in 155 source files. |
| `python -m evals.harness` | **0** | OM 34/34 `[PASS]`. No kernel rows. |
| `python -m evals.harness --all` | **0** | OM 34 `[PASS]` + kernel 30 rows (28 PASS, 2 PENDING). |

### pytest deselection (probed, not a gap)

Standing `pyproject.toml` `addopts = '-m "not integration and not probabilistic"'`. The two deselected tests are:

- `tests/evals/test_real_provider_adversarial.py::test_adversarial_probe_logs_results_when_enabled`
- `tests/splunk/test_savedsearch_generation.py::test_splunk_demo_integration_with_hec_env`

Neither is a Sprint 1 kernel ID. Collect-only `-m "integration or probabilistic"` returned exactly those two.

### Independent kernel dump (not in packet)

`run_e2e_kernel` this session: yaml_count=15, required=15, missing=[], extra=[], row_count=30, providers=`Counter({'fake': 30})`, pending only the two quality `new_build` arms, nonpass=[].

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| Capability quality `new_build` is pending, not pass | **met** | Live `--all` printed `[PENDING]` only for `cap.baseline_bag_path_a new_build` and `cap.stump_parity_guard new_build`. Live dump matches. Leak pin both arms `pass`. |
| Cite-to-subject McNemar was not implemented | **met** | `rg` over `evals/**/*.py` finds no `mcnemar`, `binomtest`, `scipy`, or `statsmodels`. `stump_pair` emits McNemar-*ready* keys only and pins `quality_win_claimed: False` (`evals/stump.py:22-42`). `cite_to_subject_primary_earned` is hardcoded `False` on kernel theater contexts (`evals/e2e_kernel.py:151,354,512`) and read as a YAML pin (`false`) for demo honesty (`use.demo_honesty_gate.yaml:12`; `e2e_kernel.py:656`). Pre-existing spike writeup under `tools/` / `docs/` is not a Sprint 1 cell. |
| No `src/praetor` correlator or envelope contract changes | **met** | `git log master..HEAD -- src/praetor` empty; `git diff master...HEAD -- src/praetor` empty. Live reads: `AlertEnvelope` two fields; supported EventIDs still `{1}` / `{4624}`. |

## 21 task verifier artifacts

All present; all `**pass**`:

| Task | Path |
|---|---|
| 01 | `.workflow/eval-kernel-01-scorecard/results/verifier-result.md` |
| 02 | `.workflow/eval-kernel-02-runner-cli/results/verifier-result.md` |
| 03 | `.workflow/eval-kernel-03-scenario-loader/results/verifier-result.md` |
| 04 | `.workflow/eval-kernel-04-theater/results/verifier-result.md` |
| 05 | `.workflow/eval-kernel-05-gov-never-contain/results/verifier-result.md` |
| 06 | `.workflow/eval-kernel-06-gov-feed-unhealthy/results/verifier-result.md` |
| 07 | `.workflow/eval-kernel-07-gov-recovery/results/verifier-result.md` |
| 08 | `.workflow/eval-kernel-08-des-envelope/results/verifier-result.md` |
| 09 | `.workflow/eval-kernel-09-des-path-b/results/verifier-result.md` |
| 10 | `.workflow/eval-kernel-10-des-evidence-hash/results/verifier-result.md` |
| 11 | `.workflow/eval-kernel-11-thr-cmdline/results/verifier-result.md` |
| 12 | `.workflow/eval-kernel-12-thr-wrong-process/results/verifier-result.md` |
| 13 | `.workflow/eval-kernel-13-thr-multi-host/results/verifier-result.md` |
| 14 | `.workflow/eval-kernel-14-use-ledger/results/verifier-result.md` |
| 15 | `.workflow/eval-kernel-15-use-progressive-auth/results/verifier-result.md` |
| 16 | `.workflow/eval-kernel-16-use-demo-honesty/results/verifier-result.md` |
| 17 | `.workflow/eval-kernel-17-cap-baseline/results/verifier-result.md` |
| 18 | `.workflow/eval-kernel-18-cap-stump/results/verifier-result.md` |
| 19 | `.workflow/eval-kernel-19-cap-label-leak/results/verifier-result.md` |
| 20 | `.workflow/eval-kernel-20-github-workflow/results/verifier-result.md` |
| 21 | `.workflow/eval-kernel-21-docs-pointer/results/verifier-result.md` |

## Independent probes (not in packet)

- Default harness path remains OM-only (no `cap.` / `gov.` / `des.` / `thr.` / `use.` lines).
- `des.envelope_rejects_extra_fields` exercises existing forbid-extra; it does not add envelope fields.
- `659b249` mypy unblock is scoped to `evals/capability/spike_vertex_provider.py` and `evals/capability_spike.py`; it does not expand CBC / envelope / EventID.
- `kernel_exit_code` treats `pending` as non-failing. That matches the written Sprint 1 honesty rule.

## Gaps

None that block Sprint 1 exit. Attempt 1's mypy gap is closed on fresh evidence.
