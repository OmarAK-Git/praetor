# corroboration-floor-02-helpers

## Goal
Relax meets_host_cited_corroboration and meets_account_corroboration to temporary >=1 floor; remove ledger_history from non-attacker set.

## Scope
provenance.py helpers + evidence unit tests only.

## Acceptance criteria
- Host: >=1 target-anchoring cite passes; zero anchors fails; sole ambiguity_flag=true cite fails; no >=2 path or trusted-path requirement.
- Account: >=1 fact of any provenance passes; empty fails.
- LEDGER_HISTORY constant may remain; is_attacker_controllable_provenance(LEDGER_HISTORY) is True.

## Files allowed
- src/praetor/evidence/provenance.py
- tests/evidence/test_host_corroboration.py
- tests/evidence/test_account_corroboration.py
- tests/evidence/test_provenance.py
- .workflow/corroboration-floor-02-helpers/

## Verification
- `pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q`
- `ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py`
- `mypy src/praetor/evidence/provenance.py`

## Tier
T2

## Researcher decision
skipped: single prescribed path from user-locked decisions

## Standing orders
- TDD: failing tests first where practical
- Do NOT commit
- Do NOT install dependencies
- Primary checkout only
