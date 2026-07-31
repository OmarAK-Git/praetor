# Code review — corroboration-floor-01-decision

**Verdict:** PASS

**Reviewer:** code-reviewer (fresh context)
**Scope:** Docs-only DEC-065 ratification (`docs/decisions.md`, `docs/contracts.md`, `docs/spec.md`, `docs/architecture.md`)
**Spec:** `.workflow/corroboration-floor-01-decision/plan.md` + code-review packet locked decisions

## Locked-decision checklist

| Locked pin | Status | Evidence |
|---|---|---|
| Temporary ≥1 anchoring cited fact (any `provenance_path`) | OK | `docs/contracts.md` §12a host/account sections; `docs/spec.md` host/account sections; DEC-065 §Temporary host/account floors |
| Sole `ambiguity_flag=true` anchoring cite still fails | OK | Host floor rule 2 + explicit failing cases in contracts §12a, spec Host Corroboration Floor, DEC-065 |
| `ledger_history` not corroboration-eligible | OK | contracts §12a table (`Corroboration-eligible: no`); DEC-064/065 narrative; supersedes DEC-064 trust extension only |
| Upgrade-to-≥2 flagged for multi-telemetry | OK | Explicit upgrade blocks in contracts §12a (host + account), DEC-065 §Upgrade flag, spec upgrade pins |
| DEC-064 OM `agentic_evidence_gathering_failed` preserved | OK | `docs/contracts.md` §13 row; DEC-064 §Outcome Matrix row unchanged |
| DEC-064 `session_trace_hash` preserved | OK | `docs/contracts.md` §Agentic session trace (`session_trace_hash`, DEC-064); DEC-064 §Session trace hash |

## Cross-doc consistency

- `docs/spec.md` Outcome Matrix host corroboration row matches `docs/contracts.md` §13 (zero anchoring cites / sole ambiguous anchoring cite; DEC-065).
- `docs/architecture.md` corroboration bullets align with DEC-065 temporary semantics.
- DEC-064 summary table row and full section mark corroboration trust extension **superseded by DEC-065** while retaining OM row and session trace hash.

## Findings

### Important (non-blocking for Task 1 scope)

1. **`docs/contracts.md:584` — “Implemented” implies runtime matches DEC-065 when code still enforces DEC-059**
   - Text: `**Implemented** in PolicyGate + `evidence/provenance.py`; harness scenario `insufficient_corroboration` (sole-ambiguous failure mode under temporary floor).`
   - `src/praetor/evidence/provenance.py` still requires ≥2 distinct `provenance_path` values and ≥1 non-attacker-controllable path (`meets_host_cited_corroboration` lines 74–77); account path still requires sysmon + security pair (`meets_account_corroboration` lines 39–40); `LEDGER_HISTORY` remains in `_NON_ATTACKER_CONTROLLABLE_PATHS`.
   - **Fix:** In Task 2 (`corroboration-floor-02-helpers`) align code and re-validate this line; or soften now to “**Contract** (code alignment: Task 2)” so authoritative docs do not overstate shipped behavior.

### Minor (track)

1. **`docs/decisions.md:355` — “trust table … unchanged”**
   - DEC-065 §Deferred enforcement says the §12a table is “unchanged for future use,” but the table was expanded (third column, `ledger_history` / `org_config_section` / `similar_cases` rows). Wording should be “expanded, advisory until multi-telemetry” not “unchanged.”

2. **`docs/decisions.md:21` — DEC-059 summary row still says “account path unchanged”**
   - Account corroboration floor is now temporarily ≥1 (DEC-065). Historical DEC-059 row is not wrong as a 2026-06-29 record, but a “superseded for floor by DEC-065” footnote would reduce confusion.

## What was checked

- `git diff` for all four allowed doc files
- `rg` for DEC-065, `ledger_history`, `session_trace_hash`, `agentic_evidence_gathering_failed` across changed docs
- `src/praetor/evidence/provenance.py` vs contracts §12a “Implemented” claim (blast radius for misleading contract language)
- Plan acceptance criteria and implementer-result acceptance table

## Rationale

All user-locked DEC-065 pins are accurately ratified across the four authoritative docs; DEC-064 corroboration supersession is clear while OM and session-trace artifacts remain. The sole Important finding is expected docs/code drift already scoped to Task 2—not a locked-decision violation—so Task 1 passes with that item tracked for helper alignment.
