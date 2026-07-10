# Workflow Plan — V2-032 Progressive Authorization Reporting

**Tier:** T2  
**Goal (verbatim):** V2-032 — Progressive authorization reporting: reporting view aggregates PolicyGate override rate and analyst annotation outcomes by target type and asset class over a window; reports are read-only decision support with no self-tuning; runbook documents SOC-led promotion/reversal workflow.

**Scope:** Progressive authorization reporting and operator docs only. Do not run V2 Gate 5 exit.

## Acceptance criteria

1. Reporting view aggregates PolicyGate override rate and analyst annotation outcomes by target type and asset class over a window.
2. Reports are read-only decision support; no self-tuning or automatic config promotion occurs.
3. Runbook documents SOC-led promotion/reversal workflow.
4. Verifier checks only V2-032 acceptance, not V2 Gate 5 completion.

## Allowed files

- `src/praetor/metrics/`
- `src/praetor/annotations/`
- `src/praetor/reporting/`
- `docs/operator_runbook.md`
- `tests/metrics/`
- `tests/annotations/`
- `specs/`, `IMPLEMENTATION_PLAN.md`, `memory-bank/tasks.md`, `memory-bank/progress.md`, `memory-bank/activeContext.md`

## Verification

```bash
pytest tests/metrics/ tests/annotations/ -q
```

## Context

- `docs/proposals/v2_implementation_plan.md` § V2-032
- Existing `MetricsCollector.record_policy_gate_result` tracks aggregate override counts; reporting needs dimensional breakdown (target_type, asset_class) plus annotation outcomes from `analyst_annotations` joined to ledger edicts/directives.
- Reports must be query-only; no config mutation paths.
