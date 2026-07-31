# Verifier Result — corroboration-floor-02-helpers

## Verdict

**PASS**

## Claim under test

Task `corroboration-floor-02-helpers` is complete: `meets_host_cited_corroboration` / `meets_account_corroboration` implement DEC-065 temporary ≥1 floor; sole ambiguous host anchoring cite fails; `LEDGER_HISTORY` constant retained and `is_attacker_controllable_provenance(LEDGER_HISTORY)` is True; evidence unit tests updated. Policy/harness (task 03) ignored per packet.

## Commands run (fresh)

### `pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q`

```
.................................                                        [100%]
33 passed in 0.30s
```

### `ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py`

```
All checks passed!
```

### `mypy src/praetor/evidence/provenance.py`

```
Success: no issues found in 1 source file
```

### Probes (independent of implementer transcript)

```
is_attacker_controllable_provenance(LEDGER_HISTORY) → True
LEDGER_HISTORY in _NON_ATTACKER_CONTROLLABLE_PATHS → False
meets_host_cited_corroboration([], ...) → False
non-target-only cites → False (zero anchors)
sole ambiguous anchoring cite → False (code path: len(anchored)==1 and ambiguity_flag)
single sysmon anchoring cite → True (via test_single_provenance_passes)
meets_account_corroboration([]) → False
meets_account_corroboration([one fact]) → True
meets_host / meets_account source: no distinct-path / trusted-path / ≥2 checks
```

## Acceptance criteria checklist

| Criterion | Result | Evidence |
|---|---|---|
| Host ≥1 target-anchoring cite passes | **PASS** | `provenance.py:55-74`; `test_host_corroboration.py:82-85` |
| Host zero anchors fails | **PASS** | `provenance.py:70-71`; probe empty + non-target-only → False |
| Host sole ambiguity fails | **PASS** | `provenance.py:72-73`; `test_host_corroboration.py:128-137` |
| No ≥2 / trusted-path requirement | **PASS** | helper source; `test_single_provenance_passes`, `test_two_attacker_controllable_paths_pass` |
| Account ≥1 any provenance passes; empty fails | **PASS** | `provenance.py:33-38`; `test_account_corroboration.py:178-185` |
| `LEDGER_HISTORY` retained; attacker-controllable True | **PASS** | `provenance.py:13,15`; `test_provenance.py:13-14`; probe |

## Attempted refutations (did not overturn)

1. **`ledger_history` sole cite still passes `meets_*`** — DEC-065 says not corroboration-eligible; Task 2 / packet AC only require removal from `_NON_ATTACKER_CONTROLLABLE_PATHS` + `is_attacker_controllable_provenance(LEDGER_HISTORY) is True`. Temporary floor wording is “any provenance”; filtering ledger out of `meets_*` is not in this task’s acceptance. Non-blocking residual.
2. **No dedicated host zero-anchor unit test** — behavior confirmed by fresh probe and `if not anchored: return False`; AC is behavior, not a named test. Non-blocking residual.
3. **Misleading host test names** (`test_security_without_host_id_does_not_corroborate_target` asserts True) — under ≥1 floor a remaining sysmon anchor correctly passes; not a semantics bug.
4. **Policy/harness still on old semantics** — ignored per packet (task 03).

## Blockers

None.

## Residual (non-blocking)

- `meets_*` do not exclude `ledger_history` facts from counting; only trust classification flipped (Task 2 scope).
- Host suite lacks an explicit empty/zero-anchor failure test.
