# Verification: TASK-004

Fresh evidence required before completion. Do not claim pass without actual results.

| ID | Check | Expected | Actual | Status |
|----|-------|----------|--------|--------|
| V-001 | Three `WriteSurface` values defined | org_config, emergency, annotation | 3 enum members | pass |
| V-002 | `soc_lead` accepted for org-config activation | Principal returned | pass | pass |
| V-003 | Wrong role rejected for org-config activation | `InsufficientRoleError` | pass | pass |
| V-004 | `soc_lead` accepted for emergency never-contain | Principal returned | pass | pass |
| V-005 | Wrong role rejected for emergency never-contain | `InsufficientRoleError` | pass | pass |
| V-006 | `analyst` accepted for annotation | Principal returned | pass | pass |
| V-007 | Wrong role rejected for annotation | `InsufficientRoleError` | pass | pass |
| V-008 | Missing token rejected on all three surfaces | `MissingTokenError` | pass (None + blank) | pass |
| V-009 | Principal identity extracted for records | identity string available | pass | pass |
| V-010 | Self-asserted identity rejected | `SelfAssertedIdentityError` | pass | pass |
| V-011 | Ledger/directive/feed not external surfaces | enforced via `guard_internal_only` | pass | pass |
| V-012 | Internal ops blocked at auth router | `authenticate_external_write` | pass | pass |
| V-013 | `TokenVerifier` protocol; map verifier for tests | pass | pass | pass |
| V-014 | No `docs/` modifications | scope guard | pass | pass |
| V-015 | Full `pytest -q` | all pass | 90 passed in 0.45s | pass |
| V-016 | `mypy src/praetor/auth` (strict) | no errors | pass | pass |
| V-017 | `ruff check src/praetor/auth tests/auth` | no errors | pass | pass |

**Status values:** `pending` | `pass` | `fail` | `skipped`

## Summary

- **Last run:** 2026-06-01 (post review) — `pytest -q`, `mypy src/praetor/auth`, `ruff check src/praetor/auth tests/auth`
- **Overall:** pass

## Gaps / skipped checks

- Full-repo `mypy src` — 14 pre-existing contract Literal assignment errors (Task 2); auth module clean
- Full-repo `ruff check src tests` — pre-existing line-length issues outside auth
- CI pipeline wiring
- Production IdP integration (operator-supplied; out of scope)
