# Verifier packet — corroboration-floor-gate

## Goal
Verify temporary corroboration floor sprint with repository-wide gates.

## Acceptance criteria
- Full pytest suite passes.
- Repository-wide ruff and mypy (src evals consumer_sdk) pass.
- All three task verifier artifacts exist and PASS.
- DEC-065 temporary floor reflected in docs and code; ledger_history not trusted.
- No AgenticJudgmentProvider runtime default wiring added.

## Evidence to inspect
- `.workflow/corroboration-floor-gate/results/gate-commands.md`
- `.workflow/corroboration-floor-gate/results/remediation.md`
- `.workflow/corroboration-floor-01-decision/results/verifier-result.md`
- `.workflow/corroboration-floor-02-helpers/results/verifier-result.md`
- `.workflow/corroboration-floor-03-gate-harness/results/verifier-result.md`
- `docs/decisions.md` DEC-065
- `src/praetor/evidence/provenance.py`
- Confirm `docs/spec.md` was reverted (frozen)

## Manual checks
- Sole ambiguity still fails host corroboration.
- Upgrade-to-≥2 flag documented in DEC-065 / contracts §12a.

Write `.workflow/corroboration-floor-gate/results/verifier-result.md` and optionally `final-report.md`.
You may re-run gate commands if evidence looks stale.
