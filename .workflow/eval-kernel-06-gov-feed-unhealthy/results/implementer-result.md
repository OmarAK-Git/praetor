# Implementer result — eval-kernel-06-gov-feed-unhealthy

## Task

Task 6 — `gov.feed_unhealthy_blocks_contain`: unhealthy revocation feed blocks `auto_contain` and still allows `standard_review` via production `process_alert_intake`.

## Files changed

| File | Rationale |
|---|---|
| `evals/e2e_scenarios/gov.feed_unhealthy_blocks_contain.yaml` | E2E scenario: `feed_unhealthy: true`, containment allowlist, both arms expect escalate + `revocation_feed_unhealthy` for auto_contain and `standard_review` for review path |
| `evals/e2e_kernel.py` | Dispatch + `_run_gov_feed_unhealthy`: `_apply_policy_setup`, explicit allowlist from `containment_allow` (same store, two intakes), scorecard pins |
| `tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py` | TDD pin test: both arms pass with expected dispositions and fault flags |

## Implementation note

Plan executor calls only `_apply_policy_setup`, but harness applies `containment_allow` when `proposed_disposition` is `auto_contain`. Scenario YAML uses `containment_allow` without `proposed_disposition` (two intakes with different dispositions). Added explicit allowlist persistence after setup — mirrors `evals/harness.py` `_run_revocation_feed_degraded_mode` — so auto_contain reaches `revocation_feed_unhealthy` instead of `containment_policy_escalation_required`.

## Verification

```
pytest tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py -q
# 1 passed in 1.68s

ruff check evals/e2e_kernel.py tests/evals/e2e/test_gov_feed_unhealthy_blocks_contain.py
# All checks passed!

mypy evals/e2e_kernel.py
# Success: no issues found in 1 source file
```

## Commit

```
feat(evals): pin gov.feed_unhealthy_blocks_contain on intake
```

Queue **not** marked done (per packet).
