# Review: TASK-029 (reopen)

## Scope adherence

- Tests + minimal conftest only; no `docs/spec.md` changes.
- Orchestrator lazy-import fix from initial TASK-029 retained (unchanged this reopen).

## Gatekeeper findings (resolved)

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| REVIEW-001 | blocker (G1) | `@pytest.mark.integration` excluded compliance tests from default CI despite local fixtures only. | Removed integration marker from all 12 tests; they run under default `pytest -q`. |
| REVIEW-002 | blocker (G2/G3) | `_eligibility` helper short-circuited to `escalate(ambiguous_target_identity)` for two-sysmon and ambiguous-only bundles; production resolves **host** target (`WORKSTATION1`) when no SID-backed account signal exists. | Negative cases now assert `evaluate_policy_gate` → `AUTO_CONTAIN` on `TargetType.HOST`; corroboration still rejected at fact level. |
| REVIEW-003 | gap (G4) | Missing corroborated + `identity.ambiguity_flag=true` case. | Added test; spec.md:309 requires escalate only when ambiguity **and** insufficient corroboration — sufficient corroboration → `AUTO_CONTAIN` when gate enabled (no `identity.py` change). |
| REVIEW-004 | gap (G5) | No end-to-end `evaluate_policy_gate` on real correlated bundle for `account_containment_disabled` / enabled paths. | Added two tests with real fixtures + `account_auto_contain_enabled` flag. |
| REVIEW-005 | hygiene (G6) | Hardcoded fault/disposition strings. | Uses `AMBIGUOUS_TARGET_IDENTITY`, `ACCOUNT_CONTAINMENT_DISABLED`, `Disposition`. |

## Production behavior notes

- **Two-sysmon / ambiguous-sysmon-only:** No `target_sid` in facts → `extract_account_identity` returns `None` → `resolve_containment_target` host-falls back per `containment_policy.py:101–112`. Not a defect; distinct from SID-present-under-corroborated path (covered in `test_policy_gate.py::test_sid_without_corroboration_escalates_without_host_fallback`).
- **Ambiguity + corroboration:** `evaluate_account_containment_eligibility` ignores `identity.ambiguity_flag` when corroboration satisfied; aligned with spec.md:309 conjunction wording.

## Gaps

- OTRF-scale fixtures deferred to TASK-030.

## safe_to_commit

yes — reopen verification green (2026-06-15)
