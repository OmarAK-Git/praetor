# Implementer result — enrichment-split-01-decision

**Model:** composer-2.5 (in-session)

## Changes

- `docs/decisions.md`: Added DEC-066 index row + full section; noted DEC-065 host path superseded.
- `docs/contracts.md` §12a: Split into host corroboration (presence) + host enrichment (cited source events); account DEC-065 unchanged.
- `docs/contracts.md` §13: Retargeted `insufficient_corroboration` row; added `insufficient_enrichment` row (SFE=false).
- `docs/spec.md`: Updated Outcome Matrix mirror, Host Corroboration and Enrichment section (DEC-066), and related pins.

## GR-0012

No `OutcomeMatrixFaultFlag` enum member added (deferred to task 03).
