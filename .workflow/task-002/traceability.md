# Traceability: task-002

Map requirements → internal batches → code → verification. Code artifacts empty until implementation.

**Authority chain:** `docs/contracts.md` + `docs/spec.md` + `docs/plan.md` + `docs/prd.md` → Pydantic models → generated `schemas/*.json` (artifacts only).

| Req ID | Requirement (summary) | Batch | Code / artifact | Verification |
|--------|-------------------------|-------|-----------------|--------------|
| REQ-001 | Round-trip serialization | B-002 | `src/praetor/contracts/*.py`, `tests/contracts/test_roundtrip.py` | V-001 |
| REQ-002 | Reject `pass` | B-001, B-003 | `contracts/disposition.py`, `test_validators.py` | V-002 |
| REQ-003 | `AnalystAnnotation` both directions | B-003 | `contracts/governance.py` | V-003 |
| REQ-004 | `DecisionEdict` fields + `record_type` | B-002, B-003 | `contracts/edict.py` | V-004 |
| REQ-005 | `ContainmentDirective` shape, 300s, no feed id | B-002, B-003 | `contracts/containment.py` | V-005, V-006 |
| REQ-006 | `NeverContainSnapshotRecord` | B-002, B-003 | `contracts/ledger.py` | V-007 |
| REQ-007 | `EmergencyNeverContainRecord` + 48h | B-002, B-003 | `contracts/ledger.py` | V-008 |
| REQ-008 | `DirectiveRevocationRecord` + supersession | B-002, B-003 | `contracts/ledger.py` | V-009 |
| REQ-009 | `RevocationFeedRecord` | B-002 | `contracts/feed.py` | V-010 |
| REQ-010 | Health + identity | B-002 | `contracts/health.py`, `contracts/identity.py` | V-011 |
| REQ-011 | Schema artifacts + `schema_version` | B-004 | `schema_export.py`, `schemas/*.json` | V-012, V-013 |
| REQ-012 | Distinct ledger `record_type` | B-001, B-002 | `contracts/edict.py`, `contracts/ledger.py` | V-014 |
| REQ-013 | Evidence fact provenance fields | B-002 | `contracts/evidence.py` | V-015 |
| REQ-014 | `ModelJudgment`, `PolicyGateResult` (minimal) | B-002 | `contracts/judgment.py`, `contracts/policy.py` | V-016 |
| REQ-015 | `AlertEnvelope`, `OrgConfigSnapshot` (minimal) | B-002 | `contracts/alert.py`, `contracts/org_config.py` | V-017 |
| REQ-016 | No Task 3+ behavior | B-005 | (no hashing/state/engine/policy) | V-018 |
| REQ-017 | `extra="forbid"` | B-001, B-003 | `contracts/_base.py`, all models | V-019 |
| REQ-018 | `Literal` schema_version / record_type | B-001, B-002 | per-model literals | V-020 |
| REQ-019 | Deterministic schema export | B-004 | `schema_export.py`, `test_schema_export.py` | V-021 |
| REQ-020 | Uncertainty logged, not invented | B-002+ | `.workflow/task-002/review.md`, `final-report.md` | V-022 |
| REQ-021 | No `docs/` changes | B-005 | (git diff guard or manual check) | V-023 |

## Source documents (authoritative)

| Document | Role |
|----------|------|
| `docs/plan.md` | Task 2 test-first list, files, done-when |
| `docs/spec.md` | Required fields, semantics (not generated schemas) |
| `docs/contracts.md` | Bounds §10, validators §11, artifact filenames §13 |
| `docs/prd.md` | ModelJudgment vs PolicyGate separation |
| `.workflow/task-001/final-report.md` | Harness baseline |

## Generated artifacts (non-authoritative)

| Artifact | Produced by | Verified by |
|----------|-------------|-------------|
| `schemas/*.json` (14 files) | B-004 `schema_export.py` | V-012, V-013, V-021 |

## Orphan / unmapped

- Requirements with no batch: none
- Batches with no requirement: none
- Code changes with no verification: none (pending implementation)
