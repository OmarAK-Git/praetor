# Code review — corroboration-floor-02-helpers

**Verdict:** PASS

**Reviewer:** code-reviewer (fresh context)
**Scope:** `src/praetor/evidence/provenance.py`, `tests/evidence/test_host_corroboration.py`, `tests/evidence/test_account_corroboration.py`, `tests/evidence/test_provenance.py`
**Spec:** `.workflow/corroboration-floor-02-helpers/plan.md`, implementer packet, DEC-065 (user-locked review pins)

## DEC-065 checklist (user-locked pins)

| Pin | Status | Evidence |
|---|---|---|
| Host: ≥1 target-anchoring cite passes | OK | `meets_host_cited_corroboration` returns `True` when `anchored` non-empty and not sole-ambiguous (`provenance.py:70-74`); `test_single_provenance_passes`, `test_sysmon_plus_security_same_host_passes` |
| Host: zero anchoring cites fails | OK (code) / gap (test) | `if not anchored: return False` (`provenance.py:70-71`); no dedicated unit test (see Important #1) |
| Host: sole `ambiguity_flag=true` anchoring cite fails | OK | `provenance.py:72-73`; `test_sole_ambiguous_cited_fact_fails`; multi-anchor ambiguous passes via `test_ambiguity_on_one_of_two_target_anchoring_facts_passes` |
| Account: ≥1 fact any provenance passes | OK | `meets_account_corroboration` → `len(facts) >= 1` (`provenance.py:38`); `test_sid_backed_single_fact_authorizes`, `test_any_provenance_satisfies_corroboration`, same-provenance tests |
| Account: empty fails | OK | `provenance.py:38`; `test_empty_does_not_corroborate_single_fact_passes`, `test_ambiguous_target_empty_facts_escalates` |
| `LEDGER_HISTORY` attacker-controllable | OK | Removed from `_NON_ATTACKER_CONTROLLABLE_PATHS` (`provenance.py:15`); `test_ledger_history_is_attacker_controllable` |
| No ≥2 distinct-path or trusted-path enforcement | OK | Distinct-path and `is_attacker_controllable_provenance` checks removed from `meets_host_cited_corroboration`; sysmon+security pair requirement removed from `meets_account_corroboration`; `test_two_attacker_controllable_paths_pass` |

## Findings

### Important (fix before Task 3 / full-suite gate)

1. **`tests/evidence/test_host_corroboration.py` — missing zero-anchoring-cite failure test**
   - Plan acceptance: "zero anchors fails."
   - Logic correctly returns `False` for empty `anchored` (`provenance.py:70-71`), including empty `cited`, missing `facts_by_id` entries, and cites whose facts lack matching `host_id`.
   - **Fix:** Add explicit cases, e.g. empty `cited` tuple and cited refs with no target-anchoring facts, asserting `False`.

### Minor (track)

1. **`tests/evidence/test_host_corroboration.py:108,154` — misleading test names**
   - `test_security_without_host_id_does_not_corroborate_target` and `test_non_target_host_citation_does_not_count` assert `True` under DEC-065 because one sysmon anchor suffices. Behavior is correct; names still describe pre-floor semantics.
   - **Fix:** Rename to reflect ≥1-anchor pass (e.g. `..._still_passes_with_one_anchor`).

2. **`tests/evidence/test_host_corroboration.py:1` — stale module docstring**
   - Still references "DEC-059 / V2-011" only; temporary DEC-065 floor not noted.
   - **Fix:** Add DEC-065 temporary-floor note.

3. **DEC-065 `ledger_history` not corroboration-eligible vs task "any provenance"**
   - Helpers do not exclude `ledger_history` facts from corroboration counting; a sole `ledger_history` fact would pass `meets_account_corroboration` / an anchoring `ledger_history` cite would pass host corroboration.
   - Task 2 plan explicitly scopes account/host to "any provenance" and only requires `is_attacker_controllable_provenance(LEDGER_HISTORY) is True`; full DEC-065 eligibility exclusion may belong in Task 3 policy/harness alignment.
   - **Fix:** Confirm intended deferral; if helpers must enforce eligibility now, filter `provenance_path == LEDGER_HISTORY` in both helpers and add tests.

4. **`tests/evidence/test_account_corroboration.py:12` — orchestrator pre-import**
   - `import praetor.engine.orchestrator` breaks policy↔engine circular import for isolated collection. Pragmatic but fragile coupling in evidence tests.
   - **Fix:** Track structural import-cycle fix separately; acceptable for this task.

## Correctness / security / simplicity

- **Correctness:** Sole-ambiguity check applies only when `len(anchored) == 1`, matching DEC-065. Host anchoring uses normalized `host_id` equality with strip semantics unchanged.
- **Security:** Relaxation is intentional (DEC-065 temporary floor). No new injection/deserialization surfaces. Attacker-controllable enforcement correctly deferred.
- **Simplicity:** Minimal diff; removed dead distinct-path/trust logic without speculative abstractions. `distinct_provenance_paths` retained for other callers.

## Tests

- `pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q` → **33 passed**
- `ruff check` (scoped files) → **All checks passed**
- `mypy src/praetor/evidence/provenance.py` → **Success**

## What was checked

- `git diff HEAD` for all five scoped source/test files
- Full read of `provenance.py` and three test modules
- DEC-065 section in `docs/decisions.md` and task plan/implementer packet
- Fresh pytest, ruff, mypy on verification commands from plan
- Blast radius: `meets_*` callers in `policy/gate.py`, `policy/identity.py`, `policy/containment_policy.py` (unchanged; expected Task 3)

## Rationale

Implementation matches all user-locked DEC-065 helper pins for Task 2: temporary ≥1 host/account floors, sole-ambiguity reject, `LEDGER_HISTORY` attacker-controllable, and removal of ≥2/trusted-path enforcement. Verification commands pass. The only Important item is missing explicit zero-anchor host test coverage—not a behavioral defect. PASS with tracked follow-ups for Task 3.
