# Implementer packet — corroboration-floor-02-helpers

## Objective
Implement DEC-065 temporary corroboration helpers in provenance.py and update unit tests.

## Original user goal
Temporary floor: any cited anchoring fact works (≥1). Sole ambiguity still fails. ledger_history not trusted. Account ≥1 any provenance. Attacker-controllable enforcement deferred.

## Relevant docs
- docs/superpowers/plans/2026-07-31-corroboration-floor-temporary.md Task 2
- docs/decisions.md DEC-065
- docs/contracts.md §12a
- .workflow/corroboration-floor-02-helpers/plan.md

## Allowed files
- src/praetor/evidence/provenance.py
- tests/evidence/test_host_corroboration.py
- tests/evidence/test_account_corroboration.py
- tests/evidence/test_provenance.py
- .workflow/corroboration-floor-02-helpers/

## Do not touch
- PolicyGate evaluation logic beyond what helpers already provide
- Harness YAMLs (task 03)
- docs (task 01 done)

## Acceptance criteria
- Host: ≥1 target-anchoring cite passes; zero anchors fails; sole ambiguity fails; drop ≥2 path and trusted-path checks.
- Account: ≥1 fact any provenance passes; empty fails.
- LEDGER_HISTORY may remain; is_attacker_controllable_provenance(LEDGER_HISTORY) is True.

## Verification commands
- pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q
- ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py
- mypy src/praetor/evidence/provenance.py

## Standing orders
- Do NOT mark queue done
- Do NOT commit
- Write `.workflow/corroboration-floor-02-helpers/results/implementer-result.md`
