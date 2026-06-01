# Plan: TASK-004

## Goal

Deliver **authenticated write surface primitives** per `docs/plan.md` Task 4 and `docs/spec.md` § Authentication and Authorization — three role-tagged external surfaces (`soc_lead` for org-config activation and emergency never-contain; `analyst` for annotation), token verification with verified principal extraction, and explicit separation from internal-only operations (ledger append, directive emission, feed export). Token issuance remains out of scope.

**Authority:** `docs/spec.md` § Authentication and Authorization; `docs/plan.md` Task 4. Do not modify `docs/`.

## Scope

**In scope:**

- `src/praetor/auth/principal.py` — `Principal`, roles, auth errors
- `src/praetor/auth/verifier.py` — `TokenVerifier` protocol, surface enum, authentication entry points
- `src/praetor/auth/__init__.py` — public exports
- `tests/auth/test_auth_primitives.py` — all Task 4 test-first criteria
- Update `tests/contracts/test_scope_guard.py` — allow `auth` package
- Flight Recorder + Memory Bank updates

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| HTTP/API layer | No FastAPI/REST; surfaces are Python callables |
| Token issuance | Documented out of scope per plan |
| Business logic | Org-config activation, emergency writes, annotation storage (Tasks 9, 25) |
| SQLite / ledger | Tasks 5–6, 10 |
| Docs | Any change under `docs/` |

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | Three external write surfaces exist | `docs/plan.md` Task 4 |
| REQ-002 | Org-config activation requires `soc_lead` | `docs/spec.md` § Auth |
| REQ-003 | Emergency never-contain requires `soc_lead` | `docs/spec.md` § Auth |
| REQ-004 | Annotation submission requires `analyst` | `docs/spec.md` § Auth |
| REQ-005 | Wrong role rejected on each surface | `docs/plan.md` Task 4 |
| REQ-006 | Missing token rejected on all surfaces | `docs/plan.md` Task 4 |
| REQ-007 | Verified principal identity available for records | `docs/plan.md` Task 4, `docs/spec.md` |
| REQ-008 | Ledger append, directive emission, feed export not external surfaces | `docs/plan.md` Task 4 |
| REQ-009 | Token issuance out of scope (pluggable verifier) | `docs/plan.md` Task 4, `docs/spec.md` |
| REQ-010 | No `docs/` modifications | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token format unspecified in docs | Incompatible operator IdP integration | `TokenVerifier` protocol only; test map verifier; log gap |
| Scope guard blocks `auth/` | pytest fail | Update guard in same task |
| Surfaces conflated with internal ops | Security boundary blur | Explicit `InternalOperation` enum + tests |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Workflow artifacts | — | plan, traceability, verification |
| T-002 | Tests first | T-001 | `tests/auth/test_auth_primitives.py` |
| T-003 | `principal.py` + `verifier.py` | T-002 | Implement to pass tests |
| T-004 | Scope guard update | T-003 | Allow `auth` |
| T-005 | Verification + Memory Bank | T-004 | pytest, review, final-report |

## Verification plan (summary)

- `pytest -q` all pass
- All Task 4 test-first criteria covered
- Scope guard allows `auth`, forbids other Task 5+ packages
- Record token-format gap in review.md
