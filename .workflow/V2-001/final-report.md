# Final Report — V2-001

## Summary

Ratified **DEC-058**: V2 containment authorization uses a **deployment-configurable required `default_action`** (recommended safe default: `escalate`), v1 implicit default-allow is **retired drift**, and sole matching **`escalate` rules block `auto_contain`**. Rule-action semantics and precedence are documented for V2-005/V2-006/V2-012/V2-013 implementation.

**No production behavior changes** in this task — decision and proposal docs only, plus a narrow scope-guard allowlist for the two touched proposal files.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 Posture choice | DEC-058 § Posture decision — configurable `default_action`, not hard-coded deny |
| REQ-002 Action semantics | DEC-058 action table (`allow`, `deny`, `escalate`, `auto_contain`) |
| REQ-003 Escalate blocks | DEC-058 — escalate not hint-only; V2-006 implements |
| REQ-004 Drift retired | DEC-058 + v2_hardening Item 2 `[x]` |
| REQ-005 Precedence | DEC-058 § Rule precedence |

## Files changed

- `docs/decisions.md` — DEC-058 table row + full section
- `docs/proposals/v2_hardening.md` — Item 2 ratified, open question closed
- `docs/proposals/delivery_backlog.md` — posture / escalate rows resolved
- `tests/contracts/test_scope_guard.py` — allowlist only `delivery_backlog.md` + `v2_hardening.md` under `docs/proposals/`
- `memory-bank/{tasks,activeContext,progress,decisions}.md`
- `.workflow/V2-001/{plan,state,traceability,verification,review,final-report}.md`

## Verification performed

```
python -m pytest -q
python -m ruff check tests/contracts/test_scope_guard.py
python -m mypy tests/contracts/test_scope_guard.py
```

| Check | Result |
|---|---|
| pytest | **780 passed**, 2 deselected, 1 xfailed |
| ruff (scope guard) | clean |
| mypy (scope guard) | clean |

```
rg "DEC-058" docs/
```

Hits in `decisions.md`, `v2_hardening.md`, `delivery_backlog.md` — pass

## Known gaps

- No production/schema changes — v1 still default-allows until V2-013.
- Outcome Matrix rows for `containment_policy_denied` / `containment_policy_escalation_required` deferred to V2-006.
- `docs/contracts.md` not amended (implementation task owns matrix rows).

## Follow-on required tests (implementation tasks)

### V2-005 — Strict ContainmentRule schema and scope preflight

- `scope: global` (string) fails preflight with a clear code.
- Unknown keys on `ContainmentRule` and `ContainmentPolicy` fail validation (`extra="forbid"`).

### V2-006 — Escalate rule blocks containment

- Sole `action: escalate` match blocks `auto_contain` in unit tests (`containment_policy`) and full PolicyGate tests.
- `deny` and `escalate` produce distinct documented policy results.
- `auto_contain` plus unresolved `escalate`/`deny` conflict still emits `policy_ambiguity`.

### V2-012 / V2-013 — Default action primitive and posture flip

- `default_action` required; invalid/missing values rejected at preflight.
- Scoped `allow`/`auto_contain` overrides `default_action: escalate`.
- No matching rule applies `default_action` (not implicit ALLOW).
- `configs/example_org.yaml`, eval scenarios, and walkthrough paths updated so they no longer depend on v1 default-allow.

## safe_to_commit

yes — 2026-06-29 verification green
