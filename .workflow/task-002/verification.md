# Verification: task-002

Fresh evidence required before TASK-002 completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | Round-trip tests | All §13 models serialize/deserialize without data loss | `tests/contracts/test_roundtrip.py` — 14 parametrized cases | pass |
| V-002 | Disposition guard | `pass` fails; `standard_review` accepted | `test_disposition_rejects_pass` | pass |
| V-003 | `AnalystAnnotation` | Cross-field rules both directions | `test_analyst_annotation_*` | pass |
| V-004 | `DecisionEdict` | `system_fault_escalation`; `record_type` literal `decision_edict` | `test_decision_edict_record_type_and_fault_flag` | pass |
| V-005 | `ContainmentDirective` fields | Required integration fields present | `test_containment_directive_required_fields_present` | pass |
| V-006 | `ContainmentDirective` constraints | ≤300s lifetime; `revocation_feed_id` rejected | `test_containment_directive_max_lifetime`, `test_containment_directive_rejects_revocation_feed_id` | pass |
| V-007 | `NeverContainSnapshotRecord` | Required fields; `record_type=never_contain_snapshot` | round-trip + model literals | pass |
| V-008 | `EmergencyNeverContainRecord` | Required fields; ≤48h lifetime | `test_emergency_never_contain_max_lifetime` | pass |
| V-009 | `DirectiveRevocationRecord` | Supersession rule; §11 idempotency_key_cleared; required ledger fields | `test_revocation_supersession_*`, `test_revocation_idempotency_key_cleared_only_for_manual` | pass |
| V-010 | `RevocationFeedRecord` | All Task 2 named feed fields present | round-trip fixture | pass |
| V-011 | Health + identity | Round-trip | parametrized round-trip | pass |
| V-012 | Schema artifact inventory | 14 files per `docs/contracts.md` §13 | `test_schema_export_inventory` | pass |
| V-013 | `schema_version` in artifacts | Each exported schema includes `schema_version` | `test_schema_export_includes_schema_version` | pass |
| V-014 | Ledger `record_type` uniqueness | Four distinct literal values | `test_ledger_record_types_are_distinct` | pass |
| V-015 | Evidence fact fields | `provenance_path`, `raw_source`, `ambiguity_flag` | `EvidenceFact` model + round-trip | pass |
| V-016 | Judgment contracts | Doc-named required fields | `ModelJudgment`, `PolicyGateResult` fixtures | pass |
| V-017 | Intake/config | `AlertEnvelope`, `OrgConfigSnapshot` round-trip | parametrized round-trip | pass |
| V-018 | Scope: no Task 3+ modules | No forbidden packages under `src/praetor/` | `test_forbidden_packages_absent` | pass |
| V-019 | `extra="forbid"` | Unknown field raises | `test_extra_field_forbidden` | pass |
| V-020 | `Literal` types | Invalid `record_type` / `schema_version` rejected | `test_invalid_schema_version_literal_rejected`, `test_invalid_record_type_literal_rejected` | pass |
| V-021 | Deterministic export | Two consecutive exports byte-identical | `test_schema_export_is_byte_stable` | pass |
| V-022 | Uncertainty log | Underspecified shapes listed in `review.md` | see `review.md` R-UNSPEC-* | pass |
| V-023 | No `docs/` edits | `git diff docs/` empty | `test_docs_unchanged_in_task_branch` | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Commands (executed)

```text
cd C:\Users\oalan\Praetor
python -m pip install -e ".[dev]"
python -m praetor.contracts.schema_export
pytest -q
```

Results: **40 passed** in 0.35s (includes Task 1 smoke tests). Python 3.x with Pydantic 2.12.4.

Patch re-run (2026-06-01): schema export + pytest after §11 idempotency validator and literal/record_type tests.

## Summary

- **Last run:** 2026-06-01 (post-review patch)
- **Overall:** pass

## Gaps / skipped

- Outcome Matrix eval harness (Phase 2)
- Canonical hash stability (Task 3)
- CI / ruff / mypy (not required by Task 2)

---

## Mypy diagnosis (TASK-002 reopen — pre-fix, 2026-06-01)

Command: `python -m mypy src/praetor/contracts` (also `python -m mypy src` — same 14 errors, no additional contract-layer issues).

```
src\praetor\contracts\policy.py:14: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\org_config.py:17: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\ledger.py:32: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\ledger.py:42: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\ledger.py:59: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\judgment.py:21: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\identity.py:15: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\health.py:16: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\governance.py:17: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\feed.py:16: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\evidence.py:29: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\containment.py:35: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\alert.py:17: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
src\praetor\contracts\edict.py:21: error: Incompatible types in assignment (expression has type "str", variable has type "Literal['1']")  [assignment]
Found 14 errors in 12 files (checked 16 source files)
```

### Classification (pre-fix)

| # | File:line | Field | Class | Rationale |
|---|-----------|-------|-------|-----------|
| 1 | policy.py:14 | `schema_version` | **(a) cosmetic-but-correct** | Default uses module `SCHEMA_VERSION_V1: str`, field is `Literal['1']` |
| 2 | org_config.py:17 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 3 | ledger.py:32 | `schema_version` | **(a) cosmetic-but-correct** | same (NeverContainSnapshotRecord) |
| 4 | ledger.py:42 | `schema_version` | **(a) cosmetic-but-correct** | same (EmergencyNeverContainRecord) |
| 5 | ledger.py:59 | `schema_version` | **(a) cosmetic-but-correct** | same (DirectiveRevocationRecord) |
| 6 | judgment.py:21 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 7 | identity.py:15 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 8 | health.py:16 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 9 | governance.py:17 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 10 | feed.py:16 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 11 | evidence.py:29 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 12 | containment.py:35 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 13 | alert.py:17 | `schema_version` | **(a) cosmetic-but-correct** | same |
| 14 | edict.py:21 | `schema_version` | **(a) cosmetic-but-correct** | same |

**Totals:** 14 cosmetic-but-correct (schema_version pin), **0 behavioral** (record_type) in mypy output.

**record_type behavioral review:** mypy reports no `record_type` assignment errors (defaults are inline string literals matching each `Literal[...]`). Runtime validation already rejects unknown `record_type` on `DecisionEdict` (`test_invalid_record_type_literal_rejected`). Per `docs/spec.md` / `docs/contracts.md`, unrecognized `record_type` must fail validation — confirmed via Pydantic `Literal` on each ledger model field (not a discriminated union yet; per-model class + Literal is correct for Task 2). Additional ledger `record_type` rejection tests added in fix pass (see post-fix section below).

### Post-fix (2026-06-01)

**Fix:** Centralize `SchemaVersionV1 = Literal["1"]` and `SCHEMA_VERSION_V1: SchemaVersionV1 = "1"` in `_base.py`; import in all contract modules (removed per-file `str` default mismatch).

**Behavioral tests added:** `test_ledger_record_type_unknown_or_wrong_rejected` — parametrized over all four ledger models; wrong `record_type` raises `ValidationError` (no silent coercion).

**mypy:** `python -m mypy src` → **Success: no issues found in 23 source files**

**pytest:** `pytest -q` → **94 passed**

| ID | Check | Status |
|----|-------|--------|
| V-024 | Full-repo `mypy src` clean | pass |
| V-025 | Ledger `record_type` rejection all four models | pass |


