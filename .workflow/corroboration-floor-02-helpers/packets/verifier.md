# Verifier packet — corroboration-floor-02-helpers

## Original user goal
Temporary ≥1 corroboration floor in helpers; sole ambiguity fails; ledger_history not trusted.

## Acceptance criteria
- Host: ≥1 target-anchoring cite passes; zero anchors fails; sole ambiguity fails; no ≥2/trusted-path requirement.
- Account: ≥1 fact any provenance passes; empty fails.
- LEDGER_HISTORY constant may remain; is_attacker_controllable_provenance(LEDGER_HISTORY) is True.

## Changed files
- src/praetor/evidence/provenance.py
- tests/evidence/test_host_corroboration.py
- tests/evidence/test_account_corroboration.py
- tests/evidence/test_provenance.py

## Verification commands
- pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q
- ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py
- mypy src/praetor/evidence/provenance.py

## Implementation result
`.workflow/corroboration-floor-02-helpers/results/implementer-result.md`

## Instructions
Treat implementer claims as unevidenced until re-run. Ignore harness/policy tests still expecting old semantics (task 03). Write results/verifier-result.md.
