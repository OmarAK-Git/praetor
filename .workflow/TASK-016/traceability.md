# Traceability Matrix

| Req | AC | Decision | Task | Code/Diff | Test/Check | Review | Status |
|---|---|---|---|---|---|---|---|
| REQ-001 | AC-001 | DEC-001 | TASK-001 | `src/praetor/contracts/evidence.py` (existing) | `test_evidence_fact_missing_provenance_path_rejected` | REVIEW-001 | pass |
| REQ-002 | AC-002 | DEC-002 | TASK-001 | `src/praetor/contracts/identity.py` (existing) | `test_canonical_account_identity_requires_all_fields` | REVIEW-002 | pass |
| REQ-003 | AC-003 | DEC-003 | TASK-003 | `src/praetor/policy/identity.py` | `test_sid_absent_identity_cannot_authorize_containment`, `test_whitespace_sid_is_not_sid_backed` | REVIEW-003 | pass |
| REQ-004 | AC-004 | DEC-004 | TASK-002 | `src/praetor/evidence/provenance.py` | `test_same_provenance_facts_do_not_corroborate`, `test_two_security_logs_do_not_corroborate` | REVIEW-004 | pass |
| REQ-005 | AC-005 | DEC-005 | TASK-002 | `src/praetor/evidence/provenance.py` | `test_sysmon_plus_security_log_satisfies_corroboration`, `test_single_and_empty_do_not_corroborate`, `test_corroboration_requires_windows_security_source` | REVIEW-005 | pass |
| REQ-006 | AC-006 | DEC-004 | TASK-003 | `src/praetor/policy/identity.py` | `test_ambiguous_target_insufficient_corroboration_escalates`, `test_sid_backed_insufficient_not_flagged_escalates`, `test_synthetic_fixture_ambiguous_insufficient_escalates` | REVIEW-006 | pass |
| REQ-005 | AC-007 | DEC-007 | TASK-001 | `tests/fixtures/synthetic/*.json` | `test_synthetic_fixture_corroboration_pair`, `test_sid_backed_corroborated_authorizes_containment` | REVIEW-007 | pass |
| REQ-003 | AC-003 | DEC-008 | TASK-003 | `src/praetor/policy/identity.py` | `test_sid_backed_corroborated_authorizes_containment` | REVIEW-008 | pass |

## Decisions

| ID | Decision |
|---|---|
| DEC-001 | `provenance_path` remains a required `EvidenceFact` contract field; TASK-016 tests enforce it without doc changes. |
| DEC-002 | SID-absent means empty/whitespace `sid` on `CanonicalAccountIdentity`; name-only identities use empty SID. |
| DEC-003 | v1 corroboration requires both `sysmon_event_log` and `windows_security_log` provenance paths (spec Windows/Sysmon pair). |
| DEC-004 | `ambiguous_target_identity` escalation is unconditional on insufficient corroboration or SID absence per Outcome Matrix `docs/spec.md:59`; `ambiguity_flag=true` (`spec.md:309`) is one sufficient trigger, not the only one. |
| DEC-005 | Eligibility API returns structured result for TASK-017 PolicyGate reuse; no engine wiring in TASK-016. |
| DEC-006 | Allow `policy` package in scope guard; only `containment` remains forbidden until its task. |
| DEC-007 | Synthetic fixtures are minimal JSON fact lists consumed by corroboration tests. |
| DEC-008 | Authorized path returns `final_disposition=AUTO_CONTAIN` as eligibility signal; TASK-017 `account_containment_disabled` feature gate overrides to escalate per `docs/spec.md:311`. |
| DEC-009 | SID format validation deferred for synthetic v1; any non-empty/non-whitespace string is SID-backed. |
