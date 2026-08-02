# Test-runner result — capability-spike-gate (phase_exit)

- **model:** test-runner subagent
- **timestamp:** 2026-08-01
- **repo:** C:\Users\oalan\Praetor

## Gate commands

| # | Command | Exit | Result | Key summary |
|---|---------|------|--------|-------------|
| 1 | `pytest -q` | 0 | **PASS** | 1146 passed, 2 deselected in 98.36s |
| 2 | `ruff check src tests evals consumer_sdk` | 0 | **PASS** | All checks passed! |
| 3 | `mypy src evals consumer_sdk` | 0 | **PASS** | Success: no issues found in 148 source files |
| 4 | `python -m evals.harness` | 0 | **PASS** | 34 scenarios [PASS] |
| 5 | `python -m evals.capability_spike` | 0 | **PASS** | `capability spike skipped: PRAETOR_CAPABILITY_SPIKE not enabled` |

### Command 1 — pytest -q

```
........................................................................ [  6%]
... (progress dots omitted) ...
1146 passed, 2 deselected in 98.36s (0:01:38)
EXIT: 0
```

**Flake check:** Not triggered — full suite passed; no rerun of `tests/runtime/test_startup_guard.py::TestSingletonLock::test_two_subprocesses_race_only_one_wins` needed.

### Command 2 — ruff check

```
All checks passed!
EXIT: 0
```

### Command 3 — mypy

```
Success: no issues found in 148 source files
EXIT: 0
```

### Command 4 — evals.harness

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
EXIT: 0
```

**Harness count:** 34 passed, 0 failed.

### Command 5 — evals.capability_spike

```
capability spike skipped: PRAETOR_CAPABILITY_SPIKE not enabled
EXIT: 0
```

## Task verifier results (all six must PASS)

| Task | File | Verdict |
|------|------|---------|
| capability-spike-01-corpus | `.workflow/capability-spike-01-corpus/results/verifier-result.md` | **PASS** |
| capability-spike-02-flatten | `.workflow/capability-spike-02-flatten/results/verifier-result.md` | **PASS** |
| capability-spike-03-bundle | `.workflow/capability-spike-03-bundle/results/verifier-result.md` | **PASS** |
| capability-spike-04-runner | `.workflow/capability-spike-04-runner/results/verifier-result.md` | **PASS** |
| capability-spike-05-score | `.workflow/capability-spike-05-score/results/verifier-result.md` | **PASS** |
| capability-spike-06-cli | `.workflow/capability-spike-06-cli/results/verifier-result.md` | **PASS** |

All six verifier artifacts exist and report PASS.

## Commit scope check

`git log --oneline --name-only 1891684 41eae19 9cb454a 37083e0 82b41ad 98debe4 2450e66`

| Commit | Message | Files changed |
|--------|---------|---------------|
| `1891684` | Add labeled anchor manifest loader for capability spike. | `evals/capability/__init__.py`, `evals/capability/corpus.py`, `tests/evals/capability/__init__.py`, `tests/evals/capability/fixtures/manifest_valid.yaml`, `tests/evals/capability/test_corpus.py` |
| `41eae19` | Add generic event flattener for capability spike Path B. | `evals/capability/flatten.py`, `tests/evals/capability/test_flatten.py` |
| `9cb454a` | Add Path B bundle builder reusing correlation window and host filters. | `evals/capability/bundle.py`, `tests/evals/capability/test_bundle.py` |
| `37083e0` | Add two-path anchor runner recording model judgment and gate outcome. | `.workflow/capability-spike-04-runner/results/implementer-result.md`, `evals/capability/runner.py`, `tests/evals/capability/test_runner.py` |
| `82b41ad` | Fix Path A spike runner to pass anchor_time into intake. | `.workflow/capability-spike-04-runner/results/implementer-result-fix.md`, `evals/capability/runner.py`, `tests/evals/capability/test_runner.py` |
| `98debe4` | Add capability spike scoring, A/B delta, and confound check. | `evals/capability/score.py`, `tests/evals/capability/test_score.py` |
| `2450e66` | Add capability spike CLI with offline-safe default. | `.workflow/capability-spike-06-cli/results/implementer-result.md`, `docs/eval_gates.md`, `evals/capability_spike.py`, `tests/evals/capability/test_cli.py` |

**Forbidden paths in these seven commits:** none.

- No `src/praetor/**` paths in any of the seven commits.
- No `evals/harness.py` edits in any of the seven commits.
- No `evals/scenarios/**` edits in any of the seven commits.

**Result:** **PASS**

## Overall gate verdict

| Check | Status |
|-------|--------|
| pytest | PASS (1146 passed, 0 failed, 2 deselected) |
| ruff | PASS |
| mypy | PASS (148 files) |
| evals.harness | PASS (34/34) |
| evals.capability_spike | PASS (exit 0 skip) |
| Six task verifiers | PASS (6/6) |
| Commit scope | PASS (no forbidden paths) |

**Gate test-runner: PASS**
