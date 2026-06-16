# Verification Ledger

| ID | Requirement | Check | Command/Evidence | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| VERIFY-001 | REQ-001–005 | Sigma rule tests | `python -m pytest -q tests/detections/test_sigma_rules.py` | pass | **18 passed** | pass |
| VERIFY-002 | REQ-001–005 | Full suite regression | `python -m pytest -q` | pass (≥705) | **723 passed**, 1 deselected, 1 xfailed | pass |
| VERIFY-003 | REQ-002 | Static typing | `python -m mypy src evals consumer_sdk` | clean | **112 files** clean | pass |
| VERIFY-004 | REQ-002 | Lint | `python -m ruff check src tests evals consumer_sdk` | clean | clean | pass |

## Hardening coverage (2026-06-16 reopen)

| Area | Tests |
|---|---|
| Negative discrimination | `test_sigma_rule_discrimination` (6 cases), `test_4624_rule_does_not_match_sysmon_process_creation` |
| pySigma textquery compile | `test_sigma_rules_compile_via_textquery_backend` |
| Case-insensitive contains | `test_contains_modifier_is_case_insensitive` (`-ENC` matches `-enc` rule) |
| ATT&CK tag ↔ mapping parity | `test_attack_tags_match_mapping` |
| Manifest gate completeness | `test_manifest_covers_committed_telemetry_fixtures` |
| Validation bar | HIGH + MEDIUM gated; `specific_instead_of_generic_logsource` excluded |

## Skipped checks

| Check | Reason | Risk |
|---|---|---|
| SPL compilation | TASK-033 scope | None for Task 32 |
| Logsource enforcement in matcher | Documented: matcher evaluates detection fields only | Low — compile smoke + discrimination tests cover intent |
