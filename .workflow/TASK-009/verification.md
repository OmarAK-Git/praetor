# Verification Ledger: TASK-009 (third reopen)

Recorded from repository root. No `PYTHONPATH` override required (`pyproject.toml` sets `pythonpath = ["src", "."]`).

| ID | Requirement | Command | Expected | Actual | Status |
|----|-------------|---------|----------|--------|--------|
| VERIFY-001 | Config tests collect | `pytest -q tests/config/` | pass | **55 passed** | pass |
| VERIFY-002 | Full suite | `pytest -q` | pass | **254 passed** | pass |
| VERIFY-003 | Types | `mypy src` | pass | Success: 51 source files | pass |
| VERIFY-004 | TASK-009 scoped lint (config core) | `ruff check src/praetor/config tests/config tests/contracts/test_org_config_contract.py` | pass | All checks passed | pass |
| VERIFY-004b | TASK-009 cross-cutting lint | See command below (org_config, domains, store, contracts tests) | pass | All checks passed | pass |
| VERIFY-005 | Example hash vector | `docs/contracts.md` §3a | matches `configs/example_org.yaml` | `8b694ab5aea32db12b6a0b89000ecb34fd1bfe8a7c70489396c18c3b9607d7d3` | pass |
| VERIFY-006 | PyYAML runtime dep | `pyproject.toml` `[project] dependencies` | includes PyYAML | present | pass |
| VERIFY-007 | Import authority | `pytest -q tests/config/` | no `tests.config.paths` / conftest-as-module errors | collect OK | pass |
| VERIFY-008 | Snapshot integrity tests | `tests/config/test_config_gate.py` | conflict/tamper/reopen | present | pass |
| VERIFY-009 | Health flush retry | `test_health_flush_retries_after_injected_failure` | pending queue survives flush failure | pass | pass |
| VERIFY-010 | Lock boundary tests | activation/emergency `_in_critical` | true inside transaction | pass | pass |

## VERIFY-004b command (cross-cutting TASK-009 paths)

```text
ruff check src/praetor/config src/praetor/contracts/org_config.py src/praetor/contracts/org_config_sections.py src/praetor/hashing/domains.py src/praetor/state/store.py src/praetor/state/sqlite_guard.py tests/config tests/contracts/test_org_config_contract.py tests/contracts/conftest.py tests/contracts/test_scope_guard.py tests/contracts/test_schema_export.py tests/contracts/test_roundtrip.py
```

## Not claimed

| Item | Notes |
|------|-------|
| Repo-wide `ruff check` | Pre-existing E501 in unrelated tests (e.g. `tests/state/`, `tests/contracts/test_validators.py`) |
| Formal TASK-009 completion | Closed 2026-06-03 after operator sign-off |
| `safe_to_commit: yes` | **yes** — evidence recorded above |

## Skipped checks

| Check | Reason | Risk |
|-------|--------|------|
| Ledger hash-chain append | Task 10 | Emergency/revocation rows in SQLite state until chain task |
| PolicyGate `config_over_budget` at intake | Task 12 | Preflight rejects over-budget activation |
