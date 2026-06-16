# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–003 | Splunk compile tests | `python -m pytest -q tests/splunk/test_savedsearch_generation.py` | pass | **13 passed**, 1 deselected | pass |
| VERIFY-002 | REQ-001–003 | Compiler check mode | `python tools/compile_sigma.py --check` | exit 0 | exit 0 | pass |
| VERIFY-003 | REQ-001–005 | Full suite regression | `python -m pytest -q` | pass (≥723) | **736 passed**, 2 deselected, 1 xfailed | pass |
| VERIFY-004 | REQ-002 | Static typing | `python -m mypy src evals consumer_sdk` | clean | **112 files** clean | pass |
| VERIFY-005 | REQ-002 | Lint | `python -m ruff check src tests evals consumer_sdk tools` | clean | clean | pass |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| Live Splunk Free demo | `@pytest.mark.integration`; requires local Splunk + HEC | Low — default suite covers compile + manifest validation |
