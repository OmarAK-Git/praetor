# Verification Ledger — V2-002

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001, REQ-004 | DEC-059 + §12a content | `rg "DEC-059" docs/decisions.md` + §12a read | Corroboration + classification documented | §12a + DEC-059 section present | pass |
| VERIFY-002 | REQ-002 | Outcome Matrix row | `rg "insufficient_corroboration" docs/contracts.md` | §13 row with SFE=false | Row at §13 with `false` | pass |
| VERIFY-003 | REQ-003 | Windows provenance table | §12a read | Both paths classified | `sysmon_event_log` yes; `windows_security_log` no | pass |
| VERIFY-004 | REQ-005 | Account flag preserved | `rg "ambiguous_target_identity" docs/contracts.md` | Account path unchanged | §12a account section + §13 row retained | pass |
| VERIFY-005 | Ratification | v2_hardening Item 1 | `rg "DEC-059" docs/proposals/v2_hardening.md` | `[x] Item 1` | Present + ratified status | pass |
| VERIFY-006 | Backlog | delivery_backlog | `rg "DEC-059" docs/proposals/delivery_backlog.md` | Corroboration rows updated | P0 unblocked, P1 resolved | pass |
| VERIFY-007 | No regression | Default pytest gate | `python -m pytest -q` | pass | **780 passed**, 2 deselected, 1 xfailed | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Enum / harness completeness | Decision-only; V2-011 wires `OutcomeMatrixFaultFlag` + scenario | Low — contracts §13 is SSOT |
| Full `mypy src` | No `src/` changes | None |

## Verification run (2026-06-29)

```
python -m pytest -q
rg "DEC-059" docs/
rg "insufficient_corroboration" docs/contracts.md
```

Results recorded in final-report.
