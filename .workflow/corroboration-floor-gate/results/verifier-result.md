# Verifier Result — corroboration-floor-gate (phase_exit)

## Verdict

**PASS**

## Claim under test

Sprint `corroboration-floor` phase_exit is complete when repository-wide gates pass, all three task verifier artifacts exist and PASS, DEC-065 temporary floor is reflected in docs and code (including `ledger_history` not trusted/eligible for corroboration), sole ambiguity still fails, upgrade flag is documented, `docs/spec.md` remains frozen vs HEAD, and no `AgenticJudgmentProvider` runtime default wiring was added.

## Commands run (fresh, this session)

### `pytest -q`

```
1105 passed, 2 deselected in 92.14s (0:01:32)
```

Exit 0.

### `ruff check src tests evals consumer_sdk`

```
All checks passed!
```

Exit 0.

### `mypy src evals consumer_sdk`

```
Success: no issues found in 141 source files
```

Exit 0.

## DEC-065 pin checks

| Pin | Result | Evidence |
|---|---|---|
| Temporary ≥1 floor (host/account) | **PASS** | `provenance.py:39-50,67-87`; probe single sysmon host/account → `True` |
| Sole ambiguity fails | **PASS** | `provenance.py:85-86`; probe sole ambiguous → `False`; ledger + sole ambiguous eligible → `False` |
| Upgrade-to-≥2 flag documented | **PASS** | `docs/decisions.md:361-369`; `docs/contracts.md:575,586` |
| `docs/spec.md` frozen vs HEAD | **PASS** | `git diff HEAD -- docs/spec.md` empty; still DEC-059 ≥2 wording (`docs/spec.md:325-331`); SoT is contracts §12a (`docs/decisions.md:377`) |
| No AgenticJudgmentProvider runtime default | **PASS** | `rg AgenticJudgmentProvider\(` under `src/` → no matches |
| `ledger_history` not trusted / not corroboration-eligible | **PASS** | See remediation re-check |

### Fresh probe (this session) — prior FAIL overturned

```
eligible ledger False
eligible sysmon True
ledger attacker_controllable True
account sole ledger False
account empty False
account sole sysmon True
account ledger+sysmon True
host sole ledger False
host ledger+sysmon True
host ledger+sole ambiguous eligible False
host sole ambiguous False
host single sysmon True
```

Helpers now filter via `_is_corroboration_eligible_provenance` / `_NON_CORROBORATION_ELIGIBLE_PATHS` (`provenance.py:17-22,45-49,74-77`). PolicyGate (`gate.py:354`) and account path (`containment_policy.py` / `identity.py`) call these helpers.

Regression tests: `test_sole_ledger_history_does_not_corroborate` (host + account), `test_ledger_history_plus_eligible_*`, `test_sole_ambiguous_eligible_cite_fails_after_ledger_filtered`.

DEC-065 (`docs/decisions.md:357-359`): `ledger_history` must **not** count.  
Contracts §12a (`docs/contracts.md:563`): Corroboration-eligible **no**.

## Task verifier artifacts

| Artifact | Exists | Says |
|---|---|---|
| `.workflow/corroboration-floor-01-decision/results/verifier-result.md` | yes | PASS |
| `.workflow/corroboration-floor-02-helpers/results/verifier-result.md` | yes | PASS (residual text still claims sole ledger passes — **stale**; contradicted by fresh probe above) |
| `.workflow/corroboration-floor-03-gate-harness/results/verifier-result.md` | yes | PASS |

## Attempted refutations of PASS

1. **Prior FAIL still present** — Fresh probe: sole ledger host/account → `False`. Overturned.
2. **Tests gamed / don't exercise helpers** — Host/account ledger tests call `meets_*` via `_check` / direct assert; live import probe matches. Does not overturn.
3. **PolicyGate bypasses helpers** — `gate.py` imports `meets_host_cited_corroboration`; account uses `meets_account_corroboration`. Does not overturn.
4. **Task-02 residual still documents the bug** — Artifact formally PASS; residual is stale vs current code. Non-blocking documentation drift only.
5. **`docs/spec.md` still DEC-059 ≥2** — Intentional freeze; DEC-065 SoT is contracts §12a. Does not overturn.

## Blockers

None.
