# Final Report — V2-002

## Summary

Ratified **DEC-059**: corroboration promoted from account-only behavior to a **first-class host + account authorization concept**; **`insufficient_corroboration`** pinned in Outcome Matrix (`system_fault_escalation=false`); v1 Windows provenance trust table (`sysmon_event_log` attacker-controllable, `windows_security_log` not); future `provenance_path` values default attacker-controllable until contracts update. Account `ambiguous_target_identity` path unchanged.

**No production behavior changes** in this task — decision and contracts docs only.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 First-class corroboration | `docs/contracts.md` §12a |
| REQ-002 Fault flag ratified | §13 row `insufficient_corroboration` / SFE=false |
| REQ-003 Windows classification | §12a table + DEC-059 § classification |
| REQ-004 Future normalizer default | DEC-059 + §12a fail-closed default |
| REQ-005 Account flag preserved | §12a account section + DEC-059 mapping table |

## Files changed

- `docs/contracts.md` — §12a corroboration contract; §13 Outcome Matrix row
- `docs/decisions.md` — DEC-059 table row + full section
- `docs/proposals/v2_hardening.md` — Item 1 ratified, checklist closed
- `docs/proposals/delivery_backlog.md` — P0 unblocked, P1 resolved
- `memory-bank/{tasks,activeContext,progress,decisions}.md`
- `.workflow/V2-002/{plan,state,traceability,verification,review,final-report}.md`

## Verification performed

```
python -m pytest -q
rg "DEC-059" docs/
rg "insufficient_corroboration" docs/contracts.md
```

| Check | Result |
|---|---|
| pytest | **780 passed**, 2 deselected, 1 xfailed |
| DEC-059 grep | hits in `decisions.md`, `contracts.md`, `v2_hardening.md`, `delivery_backlog.md` |
| §13 row | `insufficient_corroboration` present with SFE=false |

## Known gaps

- No enum/metrics/harness changes — adding `INSUFFICIENT_CORROBORATION` without V2-011 scenario would fail `test_outcome_matrix_completeness_guard`.
- v1 PolicyGate still ignores citation corroboration for hosts until V2-011.
- `docs/spec.md` not amended (frozen; contracts §12a carries V2 semantics).

## Follow-on required tests (V2-011)

- Host `auto_contain` with one cited provenance escalates `insufficient_corroboration`.
- Host citations spanning two distinct approved provenance paths pass only when ≥1 non-attacker-controllable.
- Sole cited `ambiguity_flag=true` fact cannot authorize host containment.
- Account corroboration behavior unchanged (`ambiguous_target_identity`).
- Harness scenario covers `insufficient_corroboration`.

## safe_to_commit

yes — 2026-06-29 verification green
