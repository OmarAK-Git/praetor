# Implementer Packet — V2-035 Statute Curation Workflow

**implementation_model:** composer-2.5-fast

## Objective

Build review-only annotation-to-proposed-statute workflow; SOC-lead promotion via full preflight + activation audit; workflow artifact with annotations, edits, reviewer, activation result.

## Allowed files

- `.workflow/`, `src/praetor/codification/`, `src/praetor/config/activation.py`
- `docs/operator_runbook.md`, `tests/codification/`, `tests/config/`
- `specs/`, `memory-bank/`

## Verification

pytest tests/codification/ tests/config/ -q

Write `.workflow/v2-035-statute-curation/results/implementer-result.md`. Do NOT mark queue done.
