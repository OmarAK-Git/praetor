# Implementer Result — V2-032 Progressive Authorization Reporting

## Files changed

| File | Rationale |
|---|---|
| `src/praetor/metrics/evaluations.py` | Append-only `policy_gate_evaluations` table schema and `record_policy_gate_evaluation` persistence |
| `src/praetor/metrics/__init__.py` | Export evaluation schema/record symbols |
| `src/praetor/reporting/__init__.py` | Package entry for read-only reporting views |
| `src/praetor/reporting/progressive_authorization.py` | `build_progressive_authorization_report` query-only aggregation by `(target_type, asset_class)` |
| `tests/metrics/test_progressive_authorization_reporting.py` | Aggregation, window filter, annotation join, read-only contract tests |
| `docs/operator_runbook.md` | SOC-led promotion/reversal workflow section |

## Design summary

### Persistence (`metrics/evaluations.py`)

- New SQLite table `policy_gate_evaluations` stores one row per PolicyGate evaluation with:
  - `decision_id`, `target_type`, `asset_class`
  - `proposed_disposition`, `final_disposition`, `overridden` flag
  - `evaluated_at` timestamp
- `record_policy_gate_evaluation` requires `critical_transaction` (matches annotation store pattern).
- Schema init via `init_policy_gate_evaluation_schema` (must be called before first write; not invoked inside record to avoid `executescript` auto-commit breaking transactions).

### Reporting (`reporting/progressive_authorization.py`)

- `build_progressive_authorization_report(conn, window_start, window_end)` performs **SELECT-only** aggregation.
- **PolicyGate metrics** per dimension: evaluation count, override count, derived override rate.
- **Annotation metrics** per dimension: joins `analyst_annotations` → `policy_gate_evaluations` on `decision_id`; filters by analyst review `timestamp` in annotation JSON; counts correct/incorrect and corrected-disposition breakdown.
- `ProgressiveAuthorizationReport.read_only` is always `True` (contract marker; no config mutation paths).

### Operator runbook

- Documents read-only report purpose, generation example, SOC-led promotion workflow (review → propose → activate via existing path → record rationale), reversal path, and explicit non-goals (no self-tuning).

## Verification

```bash
pytest tests/metrics/ tests/annotations/ -q
```

```
.......................................................                  [100%]
55 passed in 2.16s
```

## Deferred items / approval gates

1. **Scope guard (AG-0001):** `src/praetor/reporting/` is not in `tests/contracts/test_scope_guard.py` `ALLOWED_PACKAGES`. Adding it requires editing `tests/contracts/` (outside V2-032 files_allowed). Contracts test suite will fail until allowlist is widened in a follow-up task.

2. **Production schema init:** `open_state_store` does not yet call `init_policy_gate_evaluation_schema`. Tests and manual setups must init explicitly until a state-store wiring task lands (outside files_allowed).

3. **Intake wiring:** Orchestrator still calls in-process `MetricsCollector.record_policy_gate_result` only; dimensional SQLite persistence via `record_policy_gate_evaluation` is available but not yet hooked from engine intake (deferred — reporting module and tests prove aggregation contract).
