# Plan: task-002

## Goal

Deliver **versioned Pydantic v2 contract models** for all v1 types named in `docs/contracts.md` §13, with **deterministic JSON Schema artifacts** under `schemas/`, **round-trip tests**, and **documented cross-field validators** — satisfying **Task 2** in `docs/plan.md` and unblocking Task 3 (canonical hashing).

**Authority:** `docs/contracts.md`, `docs/spec.md`, `docs/plan.md`, and `docs/prd.md` are the only sources of truth for field names, types, and behavior. Exported `schemas/*.json` are **generated artifacts** for consumers and CI; they do not define or extend the contract. Any gap between docs and models is recorded in `.workflow/task-002/review.md` and `final-report.md`, not filled by invention.

## Scope

**In scope:**

- Add `pydantic>=2` to `pyproject.toml`
- `src/praetor/contracts/` — 14 models per `docs/contracts.md` §13
- **Strict contract conventions** on all models (see Implementation standards)
- **Minimal field sets** — only fields explicitly required or named in the authoritative docs; no speculative nested shapes
- `@model_validator` / field validators for `docs/contracts.md` §10–§11 rules covered by Task 2 tests
- Deterministic JSON Schema export to `schemas/` (stable bytes across runs)
- `tests/contracts/` — round-trip, negative validation, schema export, scope guard
- Single TASK-002 delivery, implemented in **five internal batches** (below)

**Out of scope (scope guard — must not appear in this task):**

| Guard | Excludes |
|-------|----------|
| Hashing | `src/praetor/hashing/`, canonical serialization, domain constants, `EMPTY_BUNDLE`, computation of `decision_id`, idempotency key, `stamp_id`, feed `record_checksum` |
| SQLite | State store, WAL, singleton, outboxes, ledger append |
| Engine | Intake pipeline, correlation, judgment orchestration, queue/latency |
| PolicyGate | Gate logic, Outcome Matrix runtime enforcement, rate limits, breakers |
| Task 3+ | Any behavior assigned to Tasks 3–35 in `docs/plan.md` |
| Docs | Modifications under `docs/` |
| Other | `PromptExcerptSet` (Task 28); org-config loader/preflight (Task 9); reference consumer (Task 21); CI / ruff / mypy |

Hash- and checksum-related fields may exist on models as **opaque strings** only; no computation.

## Implementation standards (Pydantic v2)

Apply consistently across contract models:

| Rule | Application |
|------|-------------|
| `ConfigDict(extra="forbid")` | All contract models; unknown keys must fail validation |
| `Literal[...]` | `schema_version` and `record_type` where docs fix values (e.g. `decision_edict`, `directive_revocation`) |
| `Disposition` enum | `standard_review` \| `escalate` \| `auto_contain`; reject `pass` |
| Validators | `docs/contracts.md` §11 cross-field rules and §10 lifetime bounds required by `docs/plan.md` Task 2 tests |
| Minimal nesting | If docs name a field but not its nested shape, use the narrowest type docs support (e.g. `dict[str, Any]` only when docs require opaque structured content without field list — prefer explicit sub-models only when doc lists sub-fields) |
| Uncertainty log | Any underspecified shape → document in `.workflow/task-002/review.md` (finding) and `final-report.md` (follow-up); do not invent fields to “complete” the model |

**Not in Task 2:** PolicyGate, Outcome Matrix coupling validators, or eval-harness behavior.

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | All contract models round-trip serialization | `docs/plan.md` Task 2 |
| REQ-002 | `pass` rejected as `Disposition` | `docs/plan.md` Task 2; `docs/spec.md` |
| REQ-003 | `AnalystAnnotation` cross-field validation both directions | `docs/plan.md` Task 2; `docs/contracts.md` §11 |
| REQ-004 | `DecisionEdict`: `system_fault_escalation`, `record_type=decision_edict` | `docs/plan.md` Task 2; `docs/spec.md` |
| REQ-005 | `ContainmentDirective` required fields; ≤300s lifetime; no `revocation_feed_id` | `docs/plan.md` Task 2; `docs/contracts.md` §10–§11 |
| REQ-006 | `NeverContainSnapshotRecord` + `record_type=never_contain_snapshot` | `docs/plan.md` Task 2; `docs/spec.md` |
| REQ-007 | `EmergencyNeverContainRecord` + 48h max lifetime | `docs/plan.md` Task 2; `docs/contracts.md` §10 |
| REQ-008 | `DirectiveRevocationRecord` + supersession rule | `docs/plan.md` Task 2; `docs/contracts.md` §11 |
| REQ-009 | `RevocationFeedRecord` required feed fields | `docs/plan.md` Task 2; `docs/spec.md` |
| REQ-010 | `SystemHealthAlert`, `CanonicalAccountIdentity` round-trip + export | `docs/plan.md` Task 2 |
| REQ-011 | JSON Schema artifacts for all §13 models; each includes `schema_version` | `docs/plan.md` Task 2; `docs/contracts.md` §13 |
| REQ-012 | Four distinct ledger `record_type` values | `docs/plan.md` Task 2 Done when |
| REQ-013 | `EvidenceBundle` facts: `provenance_path`, `raw_source`, `ambiguity_flag` | `docs/contracts.md` §13; `docs/spec.md` |
| REQ-014 | `ModelJudgment`, `PolicyGateResult` — only doc-named required fields | `docs/spec.md` |
| REQ-015 | `AlertEnvelope`, `OrgConfigSnapshot` — minimal doc-named fields only | `docs/contracts.md` §13; `docs/spec.md` |
| REQ-016 | No Task 3+ modules or behavior | `docs/plan.md` Task 2 Depends on: Task 1 |
| REQ-017 | `extra="forbid"` on all contract models | This plan; strict contracts |
| REQ-018 | `Literal` for fixed `schema_version` / `record_type` where specified | `docs/contracts.md` §11; `docs/spec.md` Ledger |
| REQ-019 | Exported JSON Schema bytes stable across repeated export | This plan; artifact hygiene |
| REQ-020 | Underspecified shapes documented, not invented | This plan; `review.md` / `final-report.md` |
| REQ-021 | No modifications under `docs/` | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Underspecified nested shapes (e.g. `OrgConfigSnapshot`, policy subtrees) | Invented fields drift from later tasks | Minimal doc-named fields only; log gaps in `review.md` / `final-report.md` |
| `OrgConfigSnapshot` section list in spec is broad | Over-modeling in Task 2 | Include only sections/fields explicitly named in `docs/spec.md` Org Config; defer loader/preflight semantics to Task 9 |
| SID format for account `target_id` | Validator too strict/loose | Only add SID check if `docs/contracts.md` §11 requirement is test-covered; document pattern in review if ambiguous |
| JSON Schema export nondeterminism | Noisy PR diffs | Single exporter; canonical JSON (sorted keys, stable indentation); test double-export byte equality |
| Scope creep into hashing/SQLite/engine | Task 3+ work in Task 2 | Batch 5 scope-guard tests; no imports outside `praetor.contracts` + tests |

## Internal batches (one TASK-002, sequential)

Implement in order; each batch ends with passing tests for its slice before the next.

| Batch | ID | Deliverable | Depends on |
|-------|-----|-------------|------------|
| 1 | B-001 | **Base contract conventions** — shared base/mixins, `Disposition`, `ConfigDict(extra="forbid")`, `Literal` patterns for `schema_version` / `record_type`, package scaffold + `pyproject.toml` pydantic dep | — |
| 2 | B-002 | **Core model set** — 14 models with **minimal doc-named fields** only; round-trip tests for happy paths | B-001 |
| 3 | B-003 | **Validators and negative tests** — §10–§11 rules, `pass` rejection, lifetime caps, annotation/revocation/supersession, `revocation_feed_id` forbidden | B-002 |
| 4 | B-004 | **Schema export** — deterministic writer → `schemas/*.json`; export test (inventory + byte-stable rerun + `schema_version` present) | B-002 |
| 5 | B-005 | **Scope guard tests** — assert no `hashing/`, `state/`, `engine/`, `policy/`, `sqlite`; `docs/` unchanged; full `pytest` green | B-003, B-004 |

Final step: run full verification table → update `verification.md`, `review.md`, `state.json`.

## Proposed files (implementation — not created in plan-only run)

**Create:**

| Path | Purpose |
|------|---------|
| `src/praetor/contracts/__init__.py` | Public re-exports |
| `src/praetor/contracts/_base.py` | Shared strict base, version literals pattern |
| `src/praetor/contracts/disposition.py` | `Disposition` |
| `src/praetor/contracts/alert.py` | `AlertEnvelope` |
| `src/praetor/contracts/evidence.py` | `EvidenceBundle` |
| `src/praetor/contracts/org_config.py` | `OrgConfigSnapshot` (minimal) |
| `src/praetor/contracts/judgment.py` | `ModelJudgment` |
| `src/praetor/contracts/policy.py` | `PolicyGateResult` (result shape only; no gate) |
| `src/praetor/contracts/edict.py` | `DecisionEdict` |
| `src/praetor/contracts/containment.py` | `ContainmentDirective` |
| `src/praetor/contracts/ledger.py` | Three ledger record types |
| `src/praetor/contracts/feed.py` | `RevocationFeedRecord` |
| `src/praetor/contracts/health.py` | `SystemHealthAlert` |
| `src/praetor/contracts/governance.py` | `AnalystAnnotation` |
| `src/praetor/contracts/identity.py` | `CanonicalAccountIdentity` |
| `src/praetor/contracts/schema_export.py` | Deterministic artifact writer |
| `tests/contracts/test_roundtrip.py` | Happy-path round-trips (B-002) |
| `tests/contracts/test_validators.py` | Negative / cross-field (B-003) |
| `tests/contracts/test_schema_export.py` | Deterministic export (B-004) |
| `tests/contracts/test_scope_guard.py` | Scope guard (B-005) |
| `tests/contracts/conftest.py` | Minimal fixtures (optional) |
| `schemas/*.json` | 14 generated artifacts |

**Modify:** `pyproject.toml` (add `pydantic>=2`)

**Workflow (during implementation):** `.workflow/task-002/review.md` (uncertainties), `final-report.md` (at completion)

## Verification plan (summary)

1. `pip install -e ".[dev]"` with Pydantic v2.
2. Batches B-001→B-005 complete; `pytest` exit 0.
3. All §13 schema **artifacts** exist; export is byte-stable on rerun.
4. Negative tests per `docs/plan.md` Task 2.
5. Scope guard: no hashing, SQLite, engine, PolicyGate, Task 3+ code; no `docs/` edits.

Detail: `.workflow/task-002/verification.md`.
