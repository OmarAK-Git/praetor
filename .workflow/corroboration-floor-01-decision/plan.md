# corroboration-floor-01-decision

## Goal
Ratify DEC-065 temporary corroboration floor and update contracts/spec; supersede DEC-064 ledger_history corroboration eligibility.

## Scope
Docs/decisions only; no production code changes.

## Acceptance criteria
- DEC-065 accepted: temporary >=1 anchoring cited fact (any provenance); sole ambiguity still fails; upgrade-to->=2 flagged for multi-telemetry.
- contracts.md §12a and spec.md host/account corroboration pins match DEC-065.
- DEC-064 corroboration trust extension marked superseded; agentic OM row and session_trace_hash remain.

## Files allowed
- docs/decisions.md
- docs/contracts.md
- docs/spec.md
- docs/architecture.md
- docs/superpowers/plans/2026-07-31-corroboration-floor-temporary.md
- .workflow/corroboration-floor-01-decision/

## Verification
- `rg -n "DEC-065" docs/decisions.md docs/contracts.md docs/spec.md`
- `rg -n "ledger_history" docs/decisions.md docs/contracts.md`

## Tier
T2

## Researcher decision
skipped: single prescribed path from user-locked decisions
