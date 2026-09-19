# Test-runner result — eval-kernel-sprint1-gate (attempt 2)

Verify-only. Commands run from `C:\Users\oalan\Praetor` on 2026-09-19 after mypy unblock. No edits to `src/` or `tests/`.

## 1. `pytest -q`

- **Exit code:** 0
- **Summary:** PASS — 1220 passed, 2 deselected in 261.10s (0:04:21). No failures.

```
........................................................................ [  5%]
...
....................................................................     [100%]
1220 passed, 2 deselected in 261.10s (0:04:21)
```

## 2. `ruff check src tests evals consumer_sdk`

- **Exit code:** 0
- **Summary:** PASS — All checks passed.

```
All checks passed!
```

## 3. `mypy src evals consumer_sdk`

- **Exit code:** 0
- **Summary:** PASS — no issues found in 155 source files. (Unblocked vs attempt 1.)

```
Success: no issues found in 155 source files
```

## 4. `python -m evals.harness`

- **Exit code:** 0
- **Summary:** PASS — Outcome Matrix 34/34 PASS, 0 FAIL, 0 PENDING.

```
[PASS] account_containment_enabled
[PASS] account_containment_feature_gate_disabled
[PASS] agentic_evidence_gathering_failed
[PASS] auto_contain_stamp_failed
[PASS] benign_admin_activity
[PASS] config_over_budget
[PASS] confirmed_malicious_sequence
[PASS] containment_breaker_open
[PASS] containment_policy_denied
[PASS] containment_policy_escalation_required
[PASS] correlation_failure
[PASS] duplicate_retry
[PASS] emergency_never_contain_blocks_inflight
[PASS] emergency_never_contain_intake
[PASS] incomplete_telemetry
[PASS] insufficient_corroboration
[PASS] insufficient_enrichment
[PASS] invalid_model_citation
[PASS] latency_sla_exceeded
[PASS] malformed_json
[PASS] multi_host_target_ambiguity
[PASS] never_contain_target
[PASS] noisy_correlated_real_telemetry_placeholder
[PASS] policy_ambiguity
[PASS] policy_gate_idempotency
[PASS] prompt_construction_isolation
[PASS] provider_health_breaker_open
[PASS] provider_refusal
[PASS] provider_timeout
[PASS] provider_unavailable
[PASS] queue_aging_exceeded
[PASS] rate_limit_exceeded
[PASS] revocation_feed_unhealthy_blocks_autocontain
[PASS] ticket_stamp_failed
```

## 5. `python -m evals.harness --all`

- **Exit code:** 0
- **Summary:** PASS (harness exit 0) — OM 34/34 PASS plus kernel 30 rows (28 PASS, 2 PENDING, 0 FAIL). Total printed rows: 64 (62 PASS, 2 PENDING).

### OM (34 PASS)

Same 34 `[PASS]` IDs as command 4, including `ticket_stamp_failed`.

### Kernel 30 rows

Capability (6), design (6), governance (6), threat (6), usability (6):

```
[PASS] cap.baseline_bag_path_a old_build failure_class=none
[PENDING] cap.baseline_bag_path_a new_build failure_class=none
[PASS] cap.no_label_leak_ids old_build failure_class=none
[PASS] cap.no_label_leak_ids new_build failure_class=none
[PASS] cap.stump_parity_guard old_build failure_class=none
[PENDING] cap.stump_parity_guard new_build failure_class=none
[PASS] des.envelope_rejects_extra_fields old_build failure_class=none
[PASS] des.envelope_rejects_extra_fields new_build failure_class=none
[PASS] des.evidence_hash_stable old_build failure_class=none
[PASS] des.evidence_hash_stable new_build failure_class=none
[PASS] des.path_b_stays_out_of_src old_build failure_class=none
[PASS] des.path_b_stays_out_of_src new_build failure_class=none
[PASS] gov.feed_unhealthy_blocks_contain old_build failure_class=none
[PASS] gov.feed_unhealthy_blocks_contain new_build failure_class=none
[PASS] gov.never_contain_live_shape old_build failure_class=none
[PASS] gov.never_contain_live_shape new_build failure_class=none
[PASS] gov.recovery_never_contains old_build failure_class=none
[PASS] gov.recovery_never_contains new_build failure_class=none
[PASS] thr.ambiguous_multi_host_target old_build failure_class=none
[PASS] thr.ambiguous_multi_host_target new_build failure_class=none
[PASS] thr.instruction_in_cmdline old_build failure_class=none
[PASS] thr.instruction_in_cmdline new_build failure_class=none
[PASS] thr.valid_cite_wrong_process old_build failure_class=none
[PASS] thr.valid_cite_wrong_process new_build failure_class=none
[PASS] use.demo_honesty_gate old_build failure_class=none
[PASS] use.demo_honesty_gate new_build failure_class=none
[PASS] use.progressive_auth_report old_build failure_class=none
[PASS] use.progressive_auth_report new_build failure_class=none
[PASS] use.reconstruct_from_ledger old_build failure_class=none
[PASS] use.reconstruct_from_ledger new_build failure_class=none
```

### Capability `new_build` PENDING (proved)

- `[PENDING] cap.baseline_bag_path_a new_build failure_class=none`
- `[PENDING] cap.stump_parity_guard new_build failure_class=none`
- `cap.no_label_leak_ids new_build` is `[PASS]` (not pending)

Governance, design, threat, and usability: both `old_build` and `new_build` arms PASS.

## Gate command rollup (attempt 2)

| # | Command | Exit | Result |
|---|---------|------|--------|
| 1 | `pytest -q` | 0 | 1220 passed, 2 deselected |
| 2 | `ruff check src tests evals consumer_sdk` | 0 | All checks passed |
| 3 | `mypy src evals consumer_sdk` | 0 | Success: no issues found in 155 source files |
| 4 | `python -m evals.harness` | 0 | OM 34/34 PASS |
| 5 | `python -m evals.harness --all` | 0 | OM 34 PASS + kernel 30 rows (2 capability `new_build` PENDING) |

All five gate commands exited 0. mypy is unblocked (exit 0, 155 files).
