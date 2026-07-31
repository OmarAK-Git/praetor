# corroboration-floor-gate — remediation

Run date: 2026-07-31

## Failures addressed

| # | Failure | Fix |
|---|---------|-----|
| 1 | `test_docs_changes_limited_to_sanctioned_v2_paths` — `docs/spec.md` changed while frozen | Reverted `docs/spec.md` to HEAD; added DEC-065 SoT note that `docs/contracts.md` §12a is authoritative until spec unfreeze |
| 2 | `test_non_approved_test_helper_calls_are_stable_legacy_set` — stale line numbers | Recomputed `KNOWN_LEGACY_TEST_HELPER_CALLS` from current helper call sites |
| 3 | `test_gate_fails_corroboration_when_security_dropped` — DEC-065 sysmon-only now passes | Retargeted to `test_gate_passes_corroboration_with_sysmon_only_under_dec065`; added `test_gate_fails_corroboration_when_no_facts_collected` for empty-facts failure |
| 4 | Ruff E501 at `test_correlator_identity_compliance.py:247` | Shortened docstring to ≤88 chars |
| 5 | Gate verifier FAIL — sole `ledger_history` still counted toward corroboration (DEC-065 / contracts §12a) | Added `_is_corroboration_eligible_provenance`; `meets_host_cited_corroboration` and `meets_account_corroboration` now exclude `LEDGER_HISTORY` from the ≥1 floor; sole-ambiguity checks apply to remaining eligible cites only |

## Files changed (ledger_history remediation)

- `src/praetor/evidence/provenance.py` — corroboration-eligibility filter for `ledger_history`
- `tests/evidence/test_host_corroboration.py` — sole ledger fails; ledger + eligible cite passes; sole ambiguous eligible fails after ledger filtered
- `tests/evidence/test_account_corroboration.py` — sole ledger fails; ledger + sysmon passes

## Prior remediation files (unchanged scope)

- `docs/spec.md` — reverted only
- `docs/decisions.md` — DEC-065 doc-placement SoT note
- `tests/contracts/test_policygate_boundary_guard.py` — legacy helper line numbers
- `tests/evals/test_correlation_gate.py` — DEC-065 corroboration gate tests
- `evals/correlation_gate.py` — error string updated to DEC-065 wording
- `tests/correlation/test_correlator_identity_compliance.py` — E501 fix

## Sibling check

`test_gate_fails_corroboration_when_security_provenance_wrong` — still fails via `missing required provenance_path: windows_security_log`; no change needed.

`is_attacker_controllable_provenance(LEDGER_HISTORY)` remains `True` per DEC-065 (trust classification unchanged; only corroboration eligibility excluded).

## Final gate counts

| Command | Exit | Result |
|---------|------|--------|
| `pytest -q` | 0 | **1105 passed**, 2 deselected |
| `ruff check src tests evals consumer_sdk` | 0 | **All checks passed** |
| `mypy src evals consumer_sdk` | 0 | **141 source files**, no issues |
