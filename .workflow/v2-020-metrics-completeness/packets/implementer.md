# Implementer Packet — V2-020 Metrics Production Completeness

## Objective

Complete production metrics wiring: feed export lag on export completion, LLM-failure flag guard at intake call sites, thread-safety documentation, and optional harness metrics assertions.

## Original User Goal

V2-020 — Metrics production completeness: feed export lag on completion; `record_llm_failure` uses only `LLM_FAILURE_FAULT_FLAGS`; metrics thread-safety documented or guarded.

## Relevant Docs and State

- `docs/proposals/v2_implementation_plan.md` § V2-020
- `docs/proposals/delivery_backlog.md` — TASK-028a metrics gaps
- `.workflow/_dream/playbook.digest.md`

## Allowed Files

- `src/praetor/metrics/`
- `src/praetor/engine/orchestrator.py`
- `src/praetor/revocation/exporter.py`
- `evals/harness.py`
- `evals/scenarios/`
- `docs/operator_runbook.md`
- `tests/metrics/`
- `tests/evals/`
- `specs/`
- `IMPLEMENTATION_PLAN.md`
- `memory-bank/tasks.md`
- `memory-bank/progress.md`
- `memory-bank/activeContext.md`

## Do-Not-Touch Boundaries

- Do not mark the queue item done
- Do not run phase/sprint exit verification
- Stop before dependency installs, harness config edits, clones, writes outside allowed files
- Do not implement V2-021 through V2-023

## Acceptance Criteria

1. Feed export lag is recorded on export completion, not guessed at intake.
2. `record_llm_failure` production call sites pass only `LLM_FAILURE_FAULT_FLAGS`.
3. `MetricsCollector` thread-safety is documented as single-writer or guarded with locking and a concurrency test.
4. `engine_intake` eval optionally asserts rate-counter side effects.
5. The verifier checks only V2-020 acceptance, not V2 Gate 3 completion.

## Verification Commands

```bash
pytest tests/metrics/ tests/evals/ -q
```

## Expected Result Schema

Write to `.workflow/v2-020-metrics-completeness/results/implementer-result.md` with files changed, behavior summary, test additions, verification output, approval gates.
