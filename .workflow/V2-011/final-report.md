# Final Report — V2-011

## Summary

Implemented **DEC-059 host auto-contain corroboration floor** in PolicyGate: cited facts must span ≥2 provenance paths with ≥1 non-attacker-controllable source; sole ambiguous cited fact blocks host containment; escalates `insufficient_corroboration` (`system_fault_escalation=false`). Account path unchanged.

## Completed requirements

| Requirement | Evidence |
|---|---|
| REQ-001 Single cited provenance escalates | `test_host_single_cited_provenance_escalates`, harness `insufficient_corroboration.yaml` |
| REQ-002 Sysmon+security passes when policy allows | `test_host_sysmon_security_citations_auto_contain` |
| REQ-003 Sole ambiguous cite blocks | `test_sole_ambiguous_cited_fact_escalates`, `test_sole_ambiguous_cited_fact_fails` |
| REQ-004 Account path unchanged | `test_account_path_unaffected_by_host_corroboration_flag` |
| REQ-005 Harness scenario | `evals/scenarios/insufficient_corroboration.yaml`, completeness guard |

## Files changed (worktree)

**Production**
- `src/praetor/evidence/provenance.py` — `is_attacker_controllable_provenance`, `meets_host_cited_corroboration`
- `src/praetor/policy/gate.py` — host corroboration gate
- `src/praetor/policy/identity.py` — `INSUFFICIENT_CORROBORATION` constant
- `src/praetor/metrics/events.py` — enum member
- `evals/outcome_matrix.py` — SFE polarity
- `evals/harness.py`, `evals/run_phase3_gate.py` — corroborated host bundles / phase3 checks
- `benchmarks/serialized_path.py` — benchmark host bundle citations

**Tests / scenarios**
- `tests/evidence/test_host_corroboration.py`
- `tests/policy/test_host_corroboration_gate.py`
- `tests/policy/conftest.py`, `tests/policy/test_citation_anchored_host_targeting.py`
- `tests/correlation/test_correlator_identity_compliance.py`
- `evals/scenarios/insufficient_corroboration.yaml`

**Workflow**
- `.workflow/V2-011/*`, `.gitignore` (`.worktrees/`)

## Verification (2026-06-29, worktree)

```
pip install -e ".[dev]"
python -m pytest -q --ignore=tests/splunk   → 792 passed, 1 deselected, 1 xfailed
python -m pytest -q                         → 811 passed, 2 splunk failures (baseline drift)
python -m mypy src evals consumer_sdk         → clean
python -m ruff check src tests evals consumer_sdk → clean
python -m evals.harness                       → all scenarios PASS (31 incl. insufficient_corroboration)
```

## Known gaps

- Splunk SPL drift on worktree base commit (pre-existing); not introduced by V2-011.
- Worktree created at `C:\Users\oalan\Praetor\.worktrees\feature\v2-011-host-corroboration-floor` on branch `feature/v2-011-host-corroboration-floor`.

## safe_to_commit

yes — V2-011 scope verified green (excluding unrelated splunk baseline on this worktree root)
