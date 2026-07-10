# Verifier Result — V2-021 Evidence ID Contract Pin (re-check after AC4 retry)

**role:** skeptic-verifier (adversarial, independent)
**scope:** V2-021 only. Gate 3 explicitly out of scope; no gate checks run.
**verdict:** **PASS** — the prior AC4 gap is closed and all five acceptance criteria survive independent verification.

## Claim under test

Implementer's retry claims the earlier refutation (AC4 only) is remediated: `docs/decisions.md` and `docs/proposals/delivery_backlog.md` now mark DEC-051 closed/done, with the substantive contract-pin work (AC1–AC3) unchanged and still passing.

## Evidence gathered

### Test run (reproduced independently)

```
python -m pytest tests/hashing/ tests/correlation/ -q
57 passed in 0.72s   (exit code 0)
```

Matches the implementer's reported `57 passed`.

### AC1 — contract defines preimage, domain constant, input ordering — **SURVIVES**

- `docs/contracts.md` §3b (lines 157–198) documents `SHA256(delimited([DOMAIN_EVIDENCE_ID, provenance_path, source_event_reference]))`, `evidence_id = "ev-" + digest[:32]`, and states "Three inputs in exactly this order" with `DOMAIN_EVIDENCE_ID` "always first" (`docs/contracts.md:165,173`).
- §3b.2 `source_event_reference` construction (`docs/contracts.md:186-187`) matches `src/praetor/correlation/ids.py`.

### AC2 — exact test vector pins one known evidence_id — **SURVIVES (strongly)**

Recomputed the vector **without importing any praetor code**, building the length-delimited preimage by hand:

```
preimage = b'22:praetor:v1:evidence_id16:sysmon_event_log32:microsoft-windows-sysmon:1:12345'
result   = ev-d874f190dca015a7ba7235e2e933fbd2
```

Exactly matches the pinned vector in `docs/contracts.md:197` and `tests/correlation/test_evidence_id.py:11`. `test_evidence_id_contract_vector` hardcodes the expected string and calls the real production function `derive_evidence_id` (`tests/correlation/test_evidence_id.py:15-22`) — not gamed.

### AC3 — domain-literal isolation check still passes — **SURVIVES**

- The full suite passed (57), including `tests/hashing/test_canonical.py`, which scans `src/praetor/**/*.py` for inline `praetor:v1:evidence_id` literals outside `domains.py`.

### AC4 — DEC-051 is no longer an open doc decision — **SURVIVES (prior gap closed)**

The prior refutation rested on two authoritative files still marking DEC-051 open. Both are now closed:

- `docs/decisions.md:13` — DEC-051 row now reads "…preimage, ordering, and test vector pinned in `docs/contracts.md` §3b (V2-021)" with rationale "doc decision closed — contracts §3b is authoritative for derivation." A targeted grep for `open doc decision` across `docs/` returns **no** match in `docs/decisions.md`; the phrase is gone.
- `docs/proposals/delivery_backlog.md:134` — DEC-051 backlog status is now **`Done (DEC-051, V2-021)`** (was `Open`).

The only residual mention of "open doc decision" is `docs/proposals/v2_implementation_plan.md:454`: *"Done when: DEC-051 is no longer an open doc decision."* This is the **definition-of-done / acceptance-criterion statement**, not a status marker asserting DEC-051 is currently open — it is correct to leave it as the AC text. No authoritative registry now presents DEC-051 as open.

### AC5 — verifier checks only V2-021 — satisfied. No Gate 3 or full-gate checks were run.

### Queue item untouched — out of the failure path; implementer states the queue item was not marked done.

## Attempts to refute (and why they failed)

- **"Closure only lives in the memory-bank mirror"** (the prior refutation reason): no longer true — `docs/decisions.md` and `delivery_backlog.md`, the authoritative files, both carry the closure.
- **"`open doc decision` still appears somewhere"**: the surviving occurrence is the AC/definition-of-done line in the implementation plan, which does not mark the decision open.
- **"Test vector is gamed / assertion weakened"**: refuted — the vector was reproduced from first principles with no praetor imports, and the test invokes the real `derive_evidence_id`.

## Single strongest reason the claim survives

Independent, from-scratch recomputation of the pinned `evidence_id` matches the contract, the test, and production code simultaneously; and the previously-open DEC-051 is now closed in both authoritative registries (`docs/decisions.md`, `delivery_backlog.md`) with no residual open-status marker.

## Recommendation to parent

Accept V2-021. AC1–AC5 are verified genuine with fresh evidence (57 passing tests, independent vector recompute, doc grep). The prior AC4 scope-boundary gap is resolved.
