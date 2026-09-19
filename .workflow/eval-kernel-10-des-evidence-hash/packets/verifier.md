# Verifier packet — eval-kernel-10-des-evidence-hash

Treat implementer claims as unevidenced. scope=task.

## Goal
Task 10 — des.evidence_hash_stable.

## Acceptance criteria
- Both arms pass.
- Two kernel runs of the same logical bundle produce the same evidence_bundle_hash.
- Drift is classified harness/design, not model.
- The verifier checks only Task 10 acceptance, not Sprint 1 gate completion.

## Commands
- pytest tests/evals/e2e/test_des_evidence_hash_stable.py -q
- ruff check evals/e2e_kernel.py tests/evals/e2e/test_des_evidence_hash_stable.py
- mypy evals/e2e_kernel.py

## Implementer result (unevidenced)
.workflow/eval-kernel-10-des-evidence-hash/results/implementer-result.md

Write .workflow/eval-kernel-10-des-evidence-hash/results/verifier-result.md
Outcome: pass | gaps | human_needed
