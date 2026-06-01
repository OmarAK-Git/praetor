# Plan: TASK-003

## Goal

Deliver **canonical serialization** and **hash domain constants** per `docs/contracts.md` §1–§8, with tests-first coverage from `docs/plan.md` Task 3 — unblocking state store (Task 6) and feed checksum consumers.

**Authority:** `docs/contracts.md` is SSOT for serialization rules, domain constants, input orderings, `EMPTY_BUNDLE`, feed `record_checksum`, and never-contain entry hashing. Do not modify `docs/`.

## Scope

**In scope:**

- `src/praetor/hashing/canonical.py` — `CanonicalSerializationError`, canonical serialize/hash, length-delimited concatenation, `EMPTY_BUNDLE`
- `src/praetor/hashing/domains.py` — module-level domain constants; `derive_decision_id`, `derive_idempotency_key`, `derive_stamp_id`, feed checksum, never-contain entries hash
- `src/praetor/hashing/__init__.py` — public exports
- `tests/hashing/test_canonical.py` — all Task 3 test-first criteria
- Update `tests/contracts/test_scope_guard.py` — allow `hashing` package (Task 2 guard excluded it)
- Flight Recorder + Memory Bank updates

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| State / runtime | SQLite, singleton, attempt lifecycle (Tasks 5–6) |
| Tickets | Stamp outbox implementation (Task 7) |
| Consumer verifier | Task 21 |
| Docs | Any change under `docs/` |
| Future tasks | Auth, PolicyGate, eval harness, etc. |

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-001 | Single canonical serialization for all hashes | `docs/contracts.md` §1 |
| REQ-002 | UTF-8, sorted keys, RFC3339 6-digit UTC timestamps | §1 rules 1–3 |
| REQ-003 | Reject NaN/Infinity; reject unknown fields | §1 rules 4–5 |
| REQ-004 | Absent vs null distinct | §1 rule 6 |
| REQ-005 | Length-delimited multi-input hashing | §1.1 |
| REQ-006 | Domain constants in `domains.py` only | §2 |
| REQ-007 | `decision_id` five-part delimited SHA-256 | §3 |
| REQ-008 | Idempotency key five-part delimited SHA-256 | §4 |
| REQ-009 | `EMPTY_BUNDLE` sentinel (not empty string, not empty-object hash) | §6 |
| REQ-010 | Feed `record_checksum` excludes checksum field | §7.1 |
| REQ-011 | Embedded never-contain entries hash | §8 |
| REQ-012 | `stamp_id` uses `DOMAIN_STAMP_ID` + delimited SHA-256 | §2, `docs/plan.md` Task 3 |
| REQ-013 | No inline domain string literals outside `domains.py` | §2 |
| REQ-014 | Stable hash across repeated calls | `docs/plan.md` Task 3 |
| REQ-015 | No `docs/` modifications | Scope guard |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `EMPTY_BUNDLE` preimage not named in docs | Wrong sentinel across sites | Fixed module constant `praetor:v1:empty_bundle`; log gap in review.md |
| `stamp_id` input ordering absent from contracts §3–§4 style | Wrong stamp on recovery | Mirror decision_id inputs per `docs/spec.md` "candidate decision context"; log gap |
| Scope guard blocks `hashing/` | pytest fail | Update guard in same task |
| Float edge cases | Silent non-determinism | Reject floats in canonical path |

## Task breakdown

| ID | Task | Depends on | Notes |
|----|------|------------|-------|
| T-001 | Workflow artifacts (plan, traceability, verification) | — | This file |
| T-002 | Tests first (`tests/hashing/test_canonical.py`) | T-001 | All Task 3 criteria |
| T-003 | `canonical.py` + `domains.py` | T-002 | Implement to pass tests |
| T-004 | Scope guard update | T-003 | Allow `hashing` |
| T-005 | Verification + Memory Bank | T-004 | pytest, grep domain literals |

## Verification plan (summary)

- `pytest -q` all pass
- Grep: no `praetor:v1:` literals outside `domains.py`
- `python -c` import smoke for hashing module
- Record gaps for underspecified `EMPTY_BUNDLE` preimage and `stamp_id` ordering in review.md
