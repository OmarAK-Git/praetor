# Enrichment vs corroboration — design

**Date:** 2026-08-01  
**Status:** ratified for planning (product decisions locked by user; approaches below choose implementation shape)  
**Supersedes (host path):** DEC-065 temporary cited-fact floor for host `auto_contain`  
**Preserves:** DEC-052 citation-anchored targeting; DEC-065 temporary floor for **account** until a separate decision; `ledger_history` not corroboration-eligible

## Goal

Split two authorization concerns that today’s host floor conflates:

1. **Corroboration / provenance** — prove the alert is real / not purely attacker-supplied by **presence** of independent collection paths in the evidence bundle.
2. **Enrichment** — before host `auto_contain`, require the model to **cite** enough distinct source events that containment is not a one-line story.

Wire both into real PolicyGate / contracts / Outcome Matrix / harness, and expose them as **separate** public-demo scenarios with SOC-manager copy.

## Product pins (user-ratified)

| Pin | Value |
|---|---|
| Corroboration concern | Presence of **≥2** corroboration-eligible provenance origins in the (host-scoped) evidence bundle |
| Corroboration fault | Keep / retarget **`insufficient_corroboration`** |
| Enrichment unit | **≥2 distinct source events / event series** (option 3). Same `provenance_path` may count twice if the events differ |
| Enrichment fault | **`insufficient_enrichment`** (proposed) |
| Rejected alternative | ≥2 **cited** provenance paths (would make provenance-path corroboration redundant) |
| Scope | Host `auto_contain` for enrichment; real engine wiring, not demo-only |
| Demo | Two scenarios — presence failure vs citation-depth failure — copy must not conflate them |

## Current ground truth (verified)

- Host check today: `meets_host_cited_corroboration` in `src/praetor/evidence/provenance.py` — DEC-065 temporary floor on **cited** target-anchoring facts (≥1; sole `ambiguity_flag=true` fails). Flag: `insufficient_corroboration`.
- Gate call site: `src/praetor/policy/gate.py` after DEC-052 target resolution.
- Account: temporary ≥1 supporting fact (`meets_account_corroboration`); production still feature-gated; account identity failures use `ambiguous_target_identity` (PE-0012 historical pair rule is the multi-telemetry upgrade target, not this design).
- Contracts: `docs/contracts.md` §12a, §13; decisions DEC-052 / DEC-059 / DEC-065.
- Demo thin-evidence scenario uses a **dual-provenance bundle** but cites only one ambiguous Sysmon fact — under this design that becomes an **enrichment** failure, not corroboration.

## Approaches considered

### Approach A — Bundle presence corroboration + cited-event enrichment (recommended)

| Check | Predicate | Fault |
|---|---|---|
| Corroboration | ≥2 distinct corroboration-eligible `provenance_path` values among **host-scoped bundle facts** (facts whose `normalized_fields.host_id` matches the citation-anchored target) | `insufficient_corroboration` |
| Enrichment | ≥2 distinct `source_event_reference` values among **target-anchoring cited** facts | `insufficient_enrichment` |

- DEC-052 targeting unchanged.
- DEC-065 host temporary cited ≥1 floor **superseded** by this split (new DEC).
- Sole-`ambiguity_flag` rule is **subsumed** by enrichment ≥2 (a sole cite of any kind cannot authorize).
- Trusted-path / attacker-controllable table remains **advisory** until multi-telemetry enforcement is separately restored (DEC-059 upgrade flag stays documented, not silently re-enabled).

**Pros:** Matches ratified product intent; preserves `insufficient_corroboration` for provenance presence; enrichment can use two Sysmon events without pretending that is multi-path corroboration; lands while only Sysmon+Security exist (bundles often already have both paths).  
**Cons:** Retargets OM row semantics operators learned under DEC-065 (sole-ambiguous cite → was corroboration, becomes enrichment). Requires explicit decision + harness/demo retarget.

### Approach B — Keep DEC-065 temporary cited floor; add enrichment on top

Keep host corroboration as “≥1 anchoring cite (+ sole-ambiguity)” and add enrichment as ≥2 cited source events.

**Pros:** Smaller OM-row meaning change.  
**Cons:** Leaves “corroboration” citation-based, contradicting the ratified presence definition; two citation-side checks with overlapping failure modes; delays true provenance corroboration.

### Approach C — Cited provenance-path enrichment

Require ≥2 distinct **cited** `provenance_path` values for enrichment.

**Pros:** Closer to DEC-059 wording.  
**Cons:** **User-rejected** — makes provenance-path corroboration redundant with enrichment.

## Recommendation

**Approach A.**

Corroboration answers “are there independent collection paths present for this host?” Enrichment answers “did the model cite enough distinct events to justify containment?” They compose: presence without citation depth still escalates (enrichment); citation depth without presence still escalates (corroboration).

## Explicit design answers

### 1. Exact enrichment predicate

**Pin:** count distinct `source_event_reference` strings on **target-anchoring cited** facts.

- Resolve citations via existing `validate_evidence_citations` / `ResolvedEvidenceCitation`.
- A cite **anchors** the host when the cited fact’s `normalized_fields.host_id` equals the DEC-052 target (same helper shape as today’s `_cited_fact_anchors_host`).
- Distinctness key is **`source_event_reference`** (contracts §3b.2), not `provenance_path`.
- Observational note: `evidence_id` is derived from `(provenance_path, source_event_reference)` (§3b), so counting distinct `evidence_id` among the same anchoring set is equivalent today. **Contract language pins `source_event_reference`** so “same log type, different events” stays unambiguous.
- **Not** process-chain / ProcessGuid grouping in v1 — that would invent an uncontracted “event series” aggregation. “Event series” in product language means plural discrete source events, each already identified by `source_event_reference`.

```
meets_host_cited_enrichment(cited, *, target_host_id, facts_by_id) -> bool
  anchored = target-anchoring resolved cites with corroboration-eligible provenance
            (ledger_history still excluded from counting)
  return |{ facts_by_id[c.evidence_id].source_event_reference for c in anchored }| >= 2
```

Enrichment-eligible provenance: reuse the DEC-065 exclusion — `ledger_history` (and any future non-eligible paths) must not count toward enrichment depth.

### 2. Host only, or account too?

**Pin for this change:** enrichment applies **only to host `auto_contain`**.

Account path keeps DEC-065 temporary supporting-fact floor and `ambiguous_target_identity` on identity/corroboration failure. Account enrichment (if ever) is a separate decision after account production enablement posture is revisited.

### 3. Interaction with DEC-052 / sole-ambiguity / DEC-065

| Rule | Disposition |
|---|---|
| DEC-052 citation-anchored targeting | **Keep** unchanged |
| Sole `ambiguity_flag=true` cite cannot authorize | **Subsumed** by enrichment ≥2; document subsumption in DEC; no separate sole-ambiguity branch required once enrichment is enforced |
| DEC-065 temporary host ≥1 cited floor | **Supersede** for host (new DEC). Account temporary floor **remains** |
| DEC-065 / DEC-059 upgrade flag (≥2 paths + trusted-path table enforcement) | **Keep as future upgrade** for when multi-telemetry enforcement is desired beyond presence counting; presence ≥2 eligible paths is the **live** corroboration rule now |
| `insufficient_corroboration` | **Retarget** to host-scoped bundle presence failure only |
| Attacker-controllable table | Remains **advisory** (not enforced) unless a later decision re-enables DEC-059 trusted-path enforcement |

**Evaluation order in PolicyGate (host `auto_contain` candidate path):**

1. Citation validation / DEC-052 target resolution (existing).
2. **Corroboration** (bundle presence) → `insufficient_corroboration`.
3. **Enrichment** (cited source-event depth) → `insufficient_enrichment`.
4. Never-contain / policy / rate / breaker / feed (existing).

### 4. New Outcome Matrix row (GR-0012)

| Failure class | Disposition | Fault flag | `system_fault_escalation` |
|---|---|---|---|
| Host target, insufficient cited source-event enrichment (<2 distinct `source_event_reference` among target-anchoring cites) | escalate | `insufficient_enrichment` | **false** |

Polarity rationale: deliberate policy/safety-gate enforcement (engine working as designed), same class as `insufficient_corroboration`.

**Retarget existing row:**

| Failure class | Disposition | Fault flag | `system_fault_escalation` |
|---|---|---|---|
| Host target, insufficient provenance corroboration (<2 distinct eligible `provenance_path` in host-scoped bundle) | escalate | `insufficient_corroboration` | false |

GR-0012: ratify both row texts in `docs/contracts.md` §13 in a **decision-only** task; add `OutcomeMatrixFaultFlag.INSUFFICIENT_ENRICHMENT` only in the implement task that also ships the harness scenario.

### 5. Demo scenarios (two, not one)

| Scenario key | Bundle | Citations | Expected flag | SOC copy thrust |
|---|---|---|---|---|
| `insufficient_corroboration` (retarget) | **Single** eligible provenance path for the target host | May cite that one event | `insufficient_corroboration` | “Only one kind of telemetry is present for this host — we will not auto-isolate on a single collection path.” |
| `insufficient_enrichment` (new) | **≥2** provenance paths present | Model cites **only one** source event | `insufficient_enrichment` | “The pile has more than one log source, but the model only pointed at a single event — citation depth is too thin for auto-contain.” |

Copy rules (from public-demo design): What happens / Setup / Why it matters; SOC-manager voice; no PolicyGate / provenance_path jargon in panel prose. Do **not** reuse “Thin evidence” as a label that blurs presence vs citation depth — e.g. “One log source only” vs “Model cited only one event”.

Green-path host contain demos must cite ≥2 distinct `source_event_reference` values and use dual-provenance (or otherwise host-scoped multi-path) bundles. Rename the walkthrough helper kwarg `corroborated=` → `enriched=` (or equivalent) so demo code does not lie about which check it satisfies.

### 6. Migration / temporary floor

**Yes — this can land while DEC-065 is still the temporary account story.**

- Host: new DEC (proposed **DEC-066**) supersedes DEC-065’s host temporary cited floor and installs Approach A.
- Account: DEC-065 temporary ≥1 supporting fact remains until a later decision.
- No need to wait for “real multi-telemetry beyond Sysmon+Security” to ship enrichment; enrichment deliberately allows two events of the same path.
- Presence corroboration with Sysmon+Security already present in typical correlated bundles is intentionally passable; the new operational bar for thin single-shot judgments is mostly **enrichment**.

## Contracts / code surface (implementation map)

| Area | Change |
|---|---|
| `docs/decisions.md` | DEC-066; mark DEC-065 host pins superseded; keep account |
| `docs/contracts.md` §12a | Split into corroboration (presence) + enrichment (cited events); retarget §13 rows |
| `docs/spec.md` | Mirror host pins if unfrozen / required by project sync rules |
| `src/praetor/evidence/provenance.py` | `meets_host_bundle_corroboration`; `meets_host_cited_enrichment`; retire or narrow `meets_host_cited_corroboration` |
| `src/praetor/policy/gate.py` + `identity.py` | Wire both checks; new fault constant |
| `src/praetor/metrics/events.py` (+ fault maps) | Enum member with harness scenario (GR-0012) |
| `evals/scenarios/` | Retarget `insufficient_corroboration.yaml`; add `insufficient_enrichment.yaml` |
| Synthetic fixtures | Single-path presence-fail fixture; thin-citation enrichment-fail fixture |
| Demo / notebook registry | Two scenarios + rebuild `demo/index.html` via `tools/build_demo_page.py` |

## Out of scope

- Implementing the engine change in this design pass (planning + queue load only).
- Account enrichment.
- Re-enforcing DEC-059 trusted-path (≥1 non-attacker-controllable) as a hard gate.
- ProcessGuid / process-chain aggregation as enrichment unit.
- Draining the GSD autopilot loop.

## Success criteria

- Host `auto_contain` requires both presence corroboration and cited-event enrichment.
- OM + harness cover both flags with `system_fault_escalation=false`.
- Public demo shows two dials with non-conflated SOC copy.
- DEC-052 targeting and account DEC-065 temporary floor remain intact.
- No completion claim without fresh verification evidence at drain time.
