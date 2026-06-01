# Review: task-002

## Underspecified shapes (doc gaps — not invented)

| ID | Model / field | What docs say | What is deferred | Resolution |
|----|---------------|---------------|------------------|------------|
| R-UNSPEC-001 | `EvidenceFact.normalized_fields` | Typed normalized fields per fact; no per-source schema in Task 2 | `dict[str, Any]` until Task 28 correlation | Task 28 |
| R-UNSPEC-002 | `OrgConfigSnapshot` section bodies | Section names listed in `docs/spec.md`; nested field shapes not defined | Each section is `dict[str, Any]`; loader/preflight in Task 9 | Task 9 |
| R-UNSPEC-003 | `ContainmentDirective.actuator_constraints`, `revocation_policy` | Named required fields; internal shape not specified | `dict[str, Any]` | Task 17+ |
| R-UNSPEC-004 | `NeverContainSnapshotRecord.snapshot_content` / `embedded_never_contain_entries` | Lists of never-contain entries; entry shape not fully specified | `list[dict[str, Any]]` | Task 9 / 17 |
| R-UNSPEC-005 | `EmergencyNeverContainRecord.target_specification` | Required; shape not enumerated | `dict[str, Any]` | Task 9 |
| R-UNSPEC-006 | `DecisionEdict.timing_metadata`, `ticket_stamp_payload` | Named on edict; structure not specified | `dict[str, Any]` | Task 6–7 |
| R-UNSPEC-007 | `SystemHealthAlert` | Instances named in spec; minimal `alert_code` + `emitted_at` only | Outbox delivery fields deferred | Task 8 |
| R-UNSPEC-008 | Windows SID regex | §11 requires SID form; exact pattern not in docs | `^S-1-5(?:-\d+)+$` chosen; may tighten in Task 16 | Task 16 review |
| R-UNSPEC-009 | Manual revocation reason | §11 names “SOC-lead manual-revocation trigger”; internal `reason` enum not fully mapped in docs | `RevocationReason.MANUAL` (`"manual"`) per spec trigger list | accepted for Task 2 patch |

## Review findings

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| R-001 | note | `strict=True` omitted on base config so JSON round-trip coerces datetimes/enums; `extra=forbid` retained | accepted |
| R-002 | note | `PolicyGateResult` records dispositions only; fault flags live on `DecisionEdict` per spec | accepted |
| R-003 | note | Read-only review gap: §11 `idempotency_key_cleared` coupling missing | **fixed** — validator + tests in Task 2 patch |

**Severity:** `blocker` | `major` | `minor` | `note`

## Risks (post-review)

| Risk | Status |
|------|--------|
| Org config section typing too loose for preflight | mitigated — Task 9 will tighten |
| Schema artifact drift vs models | mitigated — export test + regen command |

## Human review notes

- **Reviewer:** agent (TASK-002 implementation)
- **Date:** 2026-06-01
- **Decision:** approve

## Open items

- TASK-003 canonical hashing and hash field computation
- Task 9 org-config loader to replace opaque section dicts where shapes are defined

## Patch (read-only review follow-up, 2026-06-01)

- Added `DirectiveRevocationRecord` §11 validator: `idempotency_key_cleared` true only when `reason == RevocationReason.MANUAL` (SOC-lead manual revocation).
- Added tests: idempotency coupling, invalid `schema_version` / `record_type` literals, four distinct ledger `record_type` values.
