# Plan: TASK-010 — Hash-Chained Audit Log and Snapshot Records

## Goal

Deliver hash-chained append-only ledger per `docs/plan.md` Task 10 and `docs/spec.md` § Ledger.

**Authority:** `docs/plan.md` Task 10, `docs/spec.md` § Ledger / startup step 3, `docs/contracts.md` §1 (canonical serialization), §9 (snapshot_content hash relationship).

## Scope

**In scope:**

- `src/praetor/ledger/{hash_chain,store,startup}.py`
- `src/praetor/hashing/domains.py` — `DOMAIN_LEDGER_LINK` + link hash helper (docs gap: formula not in contracts.md; mirrors §8.1 exclude-field pattern)
- `tests/ledger/*`
- `DecisionEdict.ledger_previous_hash` nullable for genesis (`null`)
- `open_state_store` init for ledger schema (additive, no schema_version bump)
- `tests/contracts/test_scope_guard.py` — allow `ledger` package

**Out of scope:**

| Guard | Excludes |
|-------|----------|
| Wiring revocation/emergency/config paths to append | Task 11–12 |
| Feed export / recovery | Task 11 |
| `docs/` edits | Command hard limit |
| Schema export regen | Unless tests require |

## Design (docs gap documented in review)

Chain link hash (provisional until contracts § pins):

```
ledger_current_hash = SHA256( delimited([
  DOMAIN_LEDGER_LINK,
  ledger_previous_hash or "null",
  canonical_serialize(record_body_without_chain_fields)
]) )
```

- Genesis: `ledger_previous_hash = null` in stored `DecisionEdict`; `"null"` in delimited preimage.
- Non-edict records: full contract body hashed; chain metadata in `ledger_chain` table columns only.
- Four known `record_type` values; anything else is integrity violation.

## Verification plan

- `pytest -q tests/ledger/`
- `pytest -q`
- `mypy src`
- `ruff check src/praetor/ledger tests/ledger src/praetor/hashing/domains.py`

## Risks

| Risk | Mitigation |
|------|------------|
| Chain formula absent from contracts.md | Document gap; use domain-delimited + canonical body pattern consistent with §8.1 |
| DecisionEdict `ledger_previous_hash` was `str` | Change to `str \| None` for genesis null |
| Scope guard package list | Add `ledger` to allowed set |
