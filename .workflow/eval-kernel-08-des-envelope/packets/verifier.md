# Verifier packet — eval-kernel-08-des-envelope

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 8 — des.envelope_rejects_extra_fields.

## Acceptance criteria
- Both arms pass on FakeProvider.
- Extra envelope fields raise; identity-only construction succeeds.
- No AlertEnvelope field expansion in src/.
- The verifier checks only Task 8 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_des_envelope_rejects_extra_fields.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_envelope_rejects_extra_fields.py
- mypy evals/e2e_kernel.py

## Manual checks
- src/praetor/contracts/alert.py is unchanged.

## Implementer result (unevidenced)
.workflow/eval-kernel-08-des-envelope/results/implementer-result.md

Write .workflow/eval-kernel-08-des-envelope/results/verifier-result.md
Outcome: pass | gaps | human_needed
