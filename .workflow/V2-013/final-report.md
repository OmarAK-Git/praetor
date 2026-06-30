# Final Report — V2-013

## Summary

Completed **DEC-058 posture flip (Gate 2)**: eval harness, walkthrough, and example org no longer depend on implicit allow or `default_action=auto_contain` shortcuts. Auto-contain scenarios earn authority via explicit scoped `allow` rules under `default_action: escalate`.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 No-match uses `default_action` | V2-012 policy layer; `test_default_action_applies_when_no_rule_matches` |
| REQ-002 Explicit allow in evals/walkthrough | `allowlist_containment_policy` in harness; `containment_allow` in scenarios; notebook `allow_host_containment` |
| REQ-003 Example org allowlist posture | `configs/example_org.yaml` eng-pool allow rule; hash `3bf840a8…` |
| REQ-004 Gate regression | `test_no_matching_rule_escalates_at_gate` |
| REQ-005 Harness + phase3 + walkthrough | VERIFY-005–007 |

## Files changed

**Production / config**
- `configs/example_org.yaml`
- `evals/harness.py`
- `evals/run_phase3_gate.py`
- `evals/scenarios/confirmed_malicious_sequence.yaml`
- `notebooks/praetor_walkthrough.ipynb`

**Tests**
- `tests/config/shared.py`, `test_org_config_loader.py`
- `tests/policy/conftest.py`, `test_policy_gate.py`, host/citation tests
- `tests/benchmarks/test_serialized_path.py`, correlation, engine intake

**Workflow**
- `.workflow/V2-013/*`

## Verification (2026-06-29)

```
python -m pytest -q                    → 836 passed, 2 deselected, 1 xfailed
python -m mypy src evals consumer_sdk  → 118 files clean
python -m ruff check src tests evals consumer_sdk → clean
python -m evals.harness                → 31/31 PASS
python -m evals.run_phase3_gate        → all PASS
notebooks/check_walkthrough.py         → OK
```

## Known gaps

- `docs/operator_runbook.md` not updated (task lists it; `docs/` edit forbidden).

## safe_to_commit

yes — verification green
