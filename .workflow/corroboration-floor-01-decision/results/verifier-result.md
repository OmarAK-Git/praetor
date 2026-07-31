# Verifier Result — corroboration-floor-01-decision

## Verdict

**PASS**

## Claim under test

Task `corroboration-floor-01-decision` is complete: DEC-065 temporary corroboration floor is ratified in authoritative docs; contracts §12a and spec.md match; DEC-064 corroboration trust extension is superseded while OM row + `session_trace_hash` remain. Code still on ≥2 floor is out of scope (tasks 02–03).

## Commands run (fresh)

### `rg -n "DEC-065" docs/decisions.md docs/contracts.md docs/spec.md`

```
docs/contracts.md:553: ... (DEC-059, **temporary floor DEC-065**)
docs/contracts.md:557: ... (DEC-065 upgrade flag) ...
docs/contracts.md:563: ... (DEC-065 supersedes DEC-064 corroboration extension)
docs/contracts.md:569: ### Account `auto_contain` corroboration (temporary floor, DEC-065)
docs/contracts.md:577: ### Host `auto_contain` corroboration floor (temporary, DEC-065)
docs/contracts.md:610: ... DEC-065 temporary floor ...
docs/decisions.md:24: DEC-064 row — superseded-by-DEC-065 pin
docs/decisions.md:25: DEC-065 table row — ≥1 floor + upgrade flag
docs/decisions.md:310-375: DEC-064 superseded trust extension; DEC-065 full section
docs/spec.md:67,211,319,325,395-396,425,453: DEC-065 temporary floor pins
```

### `rg -n "ledger_history" docs/decisions.md docs/contracts.md`

```
docs/contracts.md:563: | ledger_history | yes (fail-closed) | **no** | ... DEC-065 supersedes DEC-064 ...
docs/decisions.md:24-25,306-359: not corroboration-eligible; supersedes DEC-064 trust extension only
```

### Additional probes

- `rg` ≥2 in contracts/spec: only in **Upgrade (multi-telemetry)** / restore wording — not as current temporary floor.
- `agentic_evidence_gathering_failed` present: `docs/contracts.md:605`, `docs/decisions.md:320`.
- `session_trace_hash` present: `docs/contracts.md:359-378`, `docs/decisions.md:324-326,375`.
- `docs/architecture.md`: temporary ≥1 / DEC-065 pins at lines 71, 82.

## Acceptance criteria checklist

| Criterion | Result | Evidence |
|---|---|---|
| DEC-065 accepted with upgrade-to-≥2 wording | **PASS** | `docs/decisions.md:332` Status accepted; `:361-369` Upgrade flag restores ≥2 distinct paths + trust enforcement |
| contracts.md §12a matches DEC-065 (temp ≥1, sole-ambiguity reject, deferred attacker-controllable, ledger_history not eligible) | **PASS** | §12a `:569-586` ≥1 host/account; sole ambiguous fail; advisory trust table; `:563` ledger_history Corroboration-eligible **no** |
| spec.md host/account corroboration pins match DEC-065 | **PASS** | `docs/spec.md:319` account ≥1; `:325-332` host ≥1 + sole-ambiguity; OM `:67` |
| DEC-064 corroboration trust extension superseded; OM + session_trace_hash remain | **PASS** | Index `:24`; section `:310-326`; contracts OM `:605` + session hash `:359-378` |

## Attempted refutations (did not overturn)

1. **DEC-059 body still states ≥2** (`docs/decisions.md:123-129`) without a superseded banner — historical decision text; DEC-065 is the active temporary pin; not required by Task 1 acceptance.
2. **§12a “any provenance_path” vs ledger_history ineligible** — mild wording tension; eligibility column + DEC-065 section explicitly exclude `ledger_history`; matches plan DEC-065 summary.
3. **§12a “Implemented” in PolicyGate / provenance.py** — docs claim ahead of code; packet instructs ignore code floor until tasks 02–03; not a Task 1 blocker.
4. **Stale ≥2 as current floor in contracts/spec** — not found outside upgrade/restore clauses.

## Blockers

None.

## Residual (non-blocking)

- Docs/code drift until tasks 02–03 (acknowledged; ignored per packet).
- Optional: soft “Implemented” phrasing in contracts §12a host paragraph until code lands.
