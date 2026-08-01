# Verifier result — enrichment-split-01-decision

**Model:** cursor-grok-4.5-high (in-session)
**Status:** PASS

## Evidence

```
rg -n "DEC-066|insufficient_enrichment|source_event_reference" docs/decisions.md docs/contracts.md docs/spec.md
```
DEC-066 present in decisions index + section; enrichment pinned to `source_event_reference`; both OM rows in contracts §13 and spec mirror.

```
rg -n "insufficient_corroboration" docs/contracts.md
```
Row retargeted to host-scoped bundle presence failure (line 617).

## Manual checks

- Enrichment unit is `source_event_reference` (not cited provenance_path): PASS
- Host-only enrichment; account stays DEC-065: PASS
- Sole-ambiguity subsumed by enrichment >=2: PASS (contracts §12a + DEC-066)
- No enum member in this task: PASS
