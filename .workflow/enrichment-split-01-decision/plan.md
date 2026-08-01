# Task: enrichment-split-01-decision

**Goal:** Ratify DEC-066: split host corroboration (bundle presence) from enrichment (cited source events); retarget insufficient_corroboration; add Outcome Matrix row for insufficient_enrichment (decision-only).

**Scope:** Docs/decisions/contracts/spec only; no production code or enum member (GR-0012).

**Acceptance criteria:**
- DEC-066 accepted: host corroboration = >=2 eligible provenance_path in host-scoped bundle; enrichment = >=2 distinct source_event_reference among target-anchoring cites; fault insufficient_enrichment SFE=false.
- insufficient_corroboration OM row retargeted to presence failure; insufficient_enrichment OM row added.
- DEC-065 host temporary cited floor marked superseded; account DEC-065 temporary floor remains.
- No OutcomeMatrixFaultFlag.INSUFFICIENT_ENRICHMENT enum member in this task (GR-0012).

**Verification commands:**
- `rg -n "DEC-066|insufficient_enrichment|source_event_reference" docs/decisions.md docs/contracts.md docs/spec.md`
- `rg -n "insufficient_corroboration" docs/contracts.md`
