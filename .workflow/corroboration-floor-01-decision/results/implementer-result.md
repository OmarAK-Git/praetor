# Implementer Result — corroboration-floor-01-decision

## Status

complete

## Summary

Ratified **DEC-065** temporary corroboration floor in authoritative docs: host `auto_contain` requires ≥1 target-anchoring cited fact (any `provenance_path`); account requires ≥1 supporting cited fact (any provenance, still feature-gated); sole `ambiguity_flag=true` anchoring cite still fails; `ledger_history` documented as **not** corroboration-eligible (supersedes DEC-064 trust-table extension only); attacker-controllable enforcement deferred with explicit multi-telemetry upgrade flag to restore DEC-059 ≥2-path floor. DEC-064 `agentic_evidence_gathering_failed` OM row and `session_trace_hash` preserved.

## Files changed

| File | Rationale |
|---|---|
| `docs/decisions.md` | Added DEC-065 table row + full section; marked DEC-064 corroboration trust extension superseded; preserved agentic OM row and session_trace_hash |
| `docs/contracts.md` | Rewrote §12a for temporary ≥1 floor, ledger_history non-eligibility, deferred trust enforcement, upgrade flag; clarified §13 `insufficient_corroboration` failing case |
| `docs/spec.md` | Synced host/account corroboration pins and Outcome Matrix row with DEC-065 |
| `docs/architecture.md` | Updated corroboration floor references to DEC-065 temporary semantics |

## Verification command outputs

### `rg -n "DEC-065" docs/decisions.md docs/contracts.md docs/spec.md`

```
docs/contracts.md:553:Corroboration is a **first-class authorization concept** for `auto_contain`, not an account-only rule (DEC-059, **temporary floor DEC-065**). ...
docs/contracts.md:557:The table below classifies paths for **future** enforcement when multi-source telemetry lands (DEC-065 upgrade flag). ...
docs/contracts.md:563:| `ledger_history` | **yes** (fail-closed default) | **no** | ...
docs/contracts.md:569:### Account `auto_contain` corroboration (temporary floor, DEC-065)
docs/contracts.md:577:### Host `auto_contain` corroboration floor (temporary, DEC-065)
docs/contracts.md:610:| Host target, insufficient cited-evidence corroboration (zero anchoring cites or sole ambiguous anchoring cite; DEC-065 temporary floor) | ...
docs/spec.md:211:... temporary host corroboration floor (DEC-065; DEC-059 upgrade path documented in contracts §12a).
docs/spec.md:319:Account containment requires **≥1** supporting cited fact ... (DEC-065 temporary floor). ...
docs/spec.md:325:## Host Corroboration Floor (DEC-065 temporary; DEC-059 upgrade path)
docs/spec.md:395-453: (multiple DEC-065 pins)
docs/decisions.md:24-25: DEC-064 superseded pin + DEC-065 table row
docs/decisions.md:310-359: DEC-064 superseded section + DEC-065 full section
```

### `rg -n "ledger_history" docs/decisions.md docs/contracts.md`

```
docs/contracts.md:563:| `ledger_history` | **yes** (fail-closed default) | **no** | Praetor-authored past-decision SoT — ...
docs/decisions.md:24: DEC-064 row — ledger_history not corroboration-eligible
docs/decisions.md:25: DEC-065 row — ledger_history not corroboration-eligible
docs/decisions.md:306-359: DEC-064/065 narrative on ledger_history non-eligibility
```

### Manual checks

- **ledger_history not corroboration-eligible:** documented in contracts §12a table (`Corroboration-eligible: no`) and DEC-065.
- **Temporary ≥1 floor and upgrade-to-≥2 flag:** explicit in DEC-065, contracts §12a host/account sections, and spec host/account sections.

## Acceptance criteria

| Criterion | Met |
|---|---|
| DEC-065 accepted with upgrade flag wording | Yes |
| §12a states temporary ≥1 floor, sole-ambiguity reject, deferred attacker-controllable enforcement, `ledger_history` not corroboration-eligible | Yes |
| DEC-064 row notes corroboration trust extension superseded by DEC-065; OM + session_trace_hash remain | Yes |
| spec.md host/account corroboration pins match DEC-065 | Yes |

## Residual risks

- **Docs/code drift until Task 2:** `src/praetor/evidence/provenance.py` still implements DEC-059 ≥2-path semantics; follow-on task `corroboration-floor-02-helpers` must align code and unit tests.
- **Harness drift until Task 3:** `evals/scenarios/insufficient_corroboration.yaml` and policy tests may still assert old single-provenance failure mode.
- **Stale design doc:** `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` still describes `ledger_history` as corroboration-eligible (out of `files_allowed` for this task).

## Blockers

None for this docs-only task.
