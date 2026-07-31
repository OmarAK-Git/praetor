# Implementer result — corroboration-floor-03-gate-harness

## Files changed

| File | Rationale |
|------|-----------|
| `evals/scenarios/insufficient_corroboration.yaml` | Retarget OM row to sole ambiguous host citation via synthetic fixture |
| `tests/fixtures/synthetic/host_sole_ambiguous_insufficient.json` | Synthetic bundle for harness sole-ambiguous host failure (required by scenario; not in packet whitelist) |
| `tests/policy/test_host_corroboration_gate.py` | Single-provenance / dual-sysmon now auto_contain; sole-ambiguous still escalates |
| `tests/policy/test_policy_gate.py` | Single-fact SID path expects `account_containment_disabled` under ≥1 account floor |
| `tests/policy/test_policygate_containment_boundary.py` | Boundary test retargeted to sole-ambiguous helper/gate rejection |
| `tests/policy/test_citation_anchored_host_targeting.py` | **Remediation:** cross-host noise + single non-ambiguous cite → `AUTO_CONTAIN` cited incident host (DEC-065) |
| `tests/engine/test_gate_target_ownership.py` | Intake insufficient-corroboration test uses sole ambiguous host cite |
| `tests/correlation/test_correlator_identity_compliance.py` | Two-sysmon host path authorizes; account ≥1 floor assertions; docstring DEC-065 |
| `evals/run_phase3_gate.py` | **Remediation:** single non-ambiguous sysmon cite auto_contains; sole ambiguous still `insufficient_corroboration`; removed redundant multi-cite check (rate-limit collision) |

## Implementation summary

- Harness `insufficient_corroboration` now uses `bundle: synthetic_fixture` pointing at a single `ambiguity_flag=true` host-anchoring fact cited on `host_id`; expects escalate / `insufficient_corroboration` / SFE=false.
- Policy gate tests no longer expect `insufficient_corroboration` for single non-ambiguous sysmon host citation or two sysmon citations on the same path.
- `test_uncited_cross_host_noise_does_not_capture_target` now expects `AUTO_CONTAIN` on `INCIDENT_HOST_ID` — citation anchoring isolates cited host from uncited cross-host bundle noise under DEC-065.
- Phase 3 gate host corroboration check: permissive allowlist + single non-ambiguous sysmon cite must `AUTO_CONTAIN`; sole ambiguous cite must escalate `insufficient_corroboration`. Dropped legacy sysmon+security multi-cite gate assert (would hit `rate_limit_exceeded` after first auto_contain on same host).
- Account-path test with SID + single fact now escalates on `account_containment_disabled` (account corroboration passes; feature gate blocks) instead of `ambiguous_target_identity`.
- Engine intake test mirrors harness: sole ambiguous host citation escalates without persisting directive.
- Correlation suite: two-sysmon-only bundle authorizes host auto_contain when policy allowlist matches `WORKSTATION1`; ambiguous-sysmon-only still escalates `insufficient_corroboration`.

## Verification

```
pytest tests/policy/ -q
70 passed in 9.57s

pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/engine/test_gate_target_ownership.py tests/evals/test_eval_harness.py -q
78 passed in 15.03s

pytest tests/policy/test_policygate_containment_boundary.py tests/correlation/test_correlator_identity_compliance.py -q
16 passed in 1.10s

pytest tests/evals/test_phase3_regression_gate.py -q
15 passed in 13.37s

ruff check tests/policy tests/engine/test_gate_target_ownership.py evals/run_phase3_gate.py
All checks passed!
```

Combined remediation suites: **179 passed**.

## Notes

- Added `tests/fixtures/synthetic/host_sole_ambiguous_insufficient.json` because `policy_gate` harness only loads bundles via `_host_bundle`, `_incomplete_account_bundle`, or `_synthetic_fixture`; no inline-fact setup exists. Required for sole-ambiguous harness scenario per DEC-065 / acceptance criteria.
- Code-review remediation (2026-07-31): missed `test_citation_anchored_host_targeting.py` and `evals/run_phase3_gate.py` in initial implement pass.

## Unresolved

- None within task scope.
