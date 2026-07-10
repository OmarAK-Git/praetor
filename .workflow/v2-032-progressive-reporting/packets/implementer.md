# Implementer Packet — V2-032 Progressive Authorization Reporting

**implementation_model:** composer-2.5-fast

## Objective

Build a read-only progressive authorization reporting view that aggregates PolicyGate override rate and analyst annotation outcomes by `target_type` and `asset_class` over a time window. Document SOC-led promotion/reversal workflow in the operator runbook.

## Original goal

V2-032 — Progressive authorization reporting: reporting view aggregates PolicyGate override rate and analyst annotation outcomes by target type and asset class over a window; reports are read-only decision support with no self-tuning; runbook documents SOC-led promotion/reversal workflow.

## Relevant docs and state

- `docs/proposals/v2_implementation_plan.md` § V2-032
- `docs/contracts.md` (target_type, disposition, annotations)
- `src/praetor/metrics/collector.py`, `src/praetor/annotations/store.py`
- `.workflow/_dream/playbook.digest.md` (AG-0001: new package may need scope-guard allowlist — but `reporting/` is in files_allowed; check if scope guard needs update; if so STOP with approval_gates — scope guard is in tests/contracts/ which is NOT in files_allowed, so document the gap in implementer-result instead of widening scope)

## Allowed files (strict)

- `src/praetor/metrics/`
- `src/praetor/annotations/`
- `src/praetor/reporting/`
- `docs/operator_runbook.md`
- `tests/metrics/`
- `tests/annotations/`
- `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Do-not-touch

- Do not run V2 Gate 5 or full-suite pytest/ruff/mypy unless task verification commands only.
- Do not mark queue item done.
- Do not install dependencies or edit `.claude`/`.codex`.
- Do not implement self-tuning or automatic config promotion.

## Acceptance criteria

1. Reporting view aggregates PolicyGate override rate and analyst annotation outcomes by target type and asset class over a window.
2. Reports are read-only decision support; no self-tuning or automatic config promotion.
3. Runbook documents SOC-led promotion/reversal workflow.

## Verification commands

```bash
pytest tests/metrics/ tests/annotations/ -q
```

## Expected result

Write `.workflow/v2-032-progressive-reporting/results/implementer-result.md` with:
- files changed
- design summary
- verification command output
- any approval_gates or deferred items

## Implementation hints

- Add `src/praetor/reporting/` with a query function (e.g. `build_progressive_authorization_report`) that accepts a SQLite connection + time window.
- Persist or derive per-evaluation rows with `target_type`, `asset_class`, `proposed_disposition`, `final_disposition`, `override` flag — likely extend metrics recording or add a small append-only `policy_gate_evaluations` table via annotations/metrics adjacent code.
- Join `analyst_annotations` to decisions to count `disposition_correct` / correction outcomes per dimension.
- Tests in `tests/metrics/` or `tests/annotations/` proving aggregation and read-only contract (no write side effects from report builder).
- Runbook section: SOC lead reviews report → proposes config change via existing activation path → no automatic promotion.
