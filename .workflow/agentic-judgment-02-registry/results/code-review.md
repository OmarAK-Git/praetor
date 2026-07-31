# Code review — agentic-judgment-02-registry

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 2 — session trace hash domain + `SessionEvidenceRegistry` (DEC-064)  
**Spec:** `docs/superpowers/plans/2026-07-30-agentic-judgment.md` Task 2; design `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md`

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Diff | `domains.py` (+`DOMAIN_SESSION_TRACE`, `compute_session_trace_hash`); new `judgment/agentic/registry.py`, `__init__.py`; new `tests/hashing/test_domains.py`, `tests/judgment/agentic/test_registry.py` |
| AG-0007 | `rg DOMAIN_SESSION_TRACE` — constant + use only in `src/praetor/hashing/domains.py`; registry imports `compute_session_trace_hash`, no inline `praetor:v1:session_trace_hash` literal |
| PolicyGate boundary | `git diff HEAD -- src/praetor/policy/` — no content changes |
| Tests (fresh run) | `pytest tests/hashing/test_domains.py tests/judgment/agentic/test_registry.py -v` → 6 passed |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| Registry API vs plan | `record_evidence` / `record_org_config` / `record_exemplars`, properties `facts` / `exemplars` / `org_config_findings`, `session_trace_hash()`, `any_evidence_source_succeeded` — matches plan Task 2 Step 7 surface for Tasks 11–12 |

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_registry.py:82`** — `test_registry_session_trace_hash_is_order_stable_and_nonempty` checks idempotence only, not that append order affects the hash. Domain-level list ordering is implicit via `canonical_serialize`; acceptable for Task 2 acceptance criteria.

2. **`docs/contracts.md`** — `DOMAIN_SESSION_TRACE` not documented yet. Implementer deferred to Task 14 per packet; plan `files_allowed` permits it but acceptance criteria do not require it here.

3. **`registry.py:89-91`** — Public mutable `*_entries` lists allow bypassing `record_*` append paths. Matches prescribed plan shape; later tasks should use `record_*` only.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `compute_session_trace_hash` deterministic, content-sensitive, 64-hex for empty session | Met — `delimited` + `canonical_serialize` + `sha256_hex`; 3 domain tests pass |
| `SessionEvidenceRegistry` records three entry types; exposes `facts` / `exemplars` / `org_config_findings` / `session_trace_hash()` | Met — succeeded-only filtering on derived views; full trace (including failures) in hash via `as_hashable()` |
| `DOMAIN_SESSION_TRACE` in `hashing/domains.py` only (AG-0007) | Met — no duplicate domain literal in `src/` or `tests/` |
| TDD per plan | Met — tests match plan Task 2 Steps 1 & 5 verbatim; implementer documented expected failures |
| Files allowed only | Met — changes confined to scoped paths; no `src/praetor/policy/` edits |
| PolicyGate evaluation logic untouched | Met — no policy module content changes |

---

## Hash determinism check

- Preimage: `delimited([DOMAIN_SESSION_TRACE, canonical_serialize(payload)])` with sorted JSON keys — consistent with `compute_ledger_link_hash` pattern.
- `as_hashable()` uses `fact.model_dump(mode="python")`; `canonical_serialize` normalizes `datetime` to RFC3339 microsecond UTC — stable for repeated calls and registry round-trip.
- Failed entries included in trace hash but excluded from `facts` / `exemplars` / `org_config_findings` — correct audit vs. citable-surface split per design.

---

## Summary

Implementation matches plan Task 2 exactly. Hash domain and registry API are ready for phases/provider consumption. Proceed to skeptic verification.
